import socketio
import uvicorn
import cv2
import numpy as np
import asyncio
from concurrent.futures import ThreadPoolExecutor

import processor_ar_game, processor_yolo, processor_effects, processor_ruler, processor_aruco, processor_Dargame

sio = socketio.AsyncServer(
    async_mode='asgi', 
    cors_allowed_origins='*',
    ping_timeout=20,  # Увеличиваем до 20 секунд
    ping_interval=5,
    max_decode_packets=50
)
app = socketio.ASGIApp(sio)
executor = ThreadPoolExecutor(max_workers=3)
processing_clients = set()

def get_delta_mask(original, processed):
    """
    Сравнивает два кадра и возвращает RGBA-маску, 
    где неизмененные пиксели — прозрачные.
    """
    # 1. Находим разницу между кадрами
    diff = cv2.absdiff(original, processed)
    # 2. Переводим в градации серого и создаем маску прозрачности (Alpha)
    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, alpha = cv2.threshold(gray_diff, 10, 255, cv2.THRESH_BINARY)
    
    # 3. Разделяем обработанный кадр на каналы и добавляем Alpha
    b, g, r = cv2.split(processed)
    rgba = cv2.merge([b, g, r, alpha])
    
    # 4. Сжимаем в WebP (он поддерживает прозрачность и весит копейки)
    _, buffer = cv2.imencode('.webp', rgba, [int(cv2.IMWRITE_WEBP_QUALITY), 65])
    return buffer.tobytes()

@sio.on('video_frame')
async def handle_frame(sid, data):
    if sid in processing_clients:
        return 

    processing_clients.add(sid)
    loop = asyncio.get_event_loop()
    
    try:
        # Получаем байты
        image_bytes = data.get('image')
        mode = data.get('mode', 'none')
        
        if not image_bytes: return

        # Выполняем в пуле потоков
        processed_bytes = await loop.run_in_executor(executor, sync_process, image_bytes, mode)
        
        if processed_bytes:
            await sio.emit('processed_frame', processed_bytes, to=sid)
            
    except Exception as e:
        print(f"Server Error: {e}")
    finally:
        processing_clients.remove(sid)

def sync_process(image_bytes, mode):
    # Декодируем оригинал
    nparr = np.frombuffer(image_bytes, np.uint8)
    original_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if original_frame is None: return None
    
    # Создаем копию для рисования, чтобы не испортить оригинал для сравнения
    frame_to_draw = original_frame.copy()

    processors = {
        'yolo': processor_yolo.process_yolo,
        'gray': processor_effects.process_gray,
        'ruler': processor_ruler.process_ruler,
        'aruco': processor_aruco.process_aruco,
        'ar_game': processor_ar_game.process_ar_game,
        'Dar_game': processor_Dargame.process_dar_game
    }

    process_func = processors.get(mode)
    if not process_func: return None

    # Запускаем процесс (он рисует прямо ПОВЕРХ frame_to_draw)
    processed_frame = process_func(frame_to_draw)

    if processed_frame is None: return None

    # Вычисляем дельту и превращаем в прозрачный WebP
    return get_delta_mask(original_frame, processed_frame)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="./key.pem",  # Путь к ключу (возьми из Nuxt)
        ssl_certfile="./cert.pem", # Путь к сертификату
        log_level="warning"
    )