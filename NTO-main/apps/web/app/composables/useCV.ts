import { io, Socket } from "socket.io-client";
import { ref } from "vue";

interface FramePayload {
  image: Blob;
  mode: string;
}

const socket = ref<Socket | null>(null);
const processedImage = ref<string | null>(null);
const isConnected = ref(false);

export const useCV = () => {
  const connectToServer = () => {
    if (socket.value?.connected) return;


    const serverUrl = `https://${window.location.hostname}:8000`;
    // alert("Пытаюсь подключиться к: " + serverUrl);
    socket.value = io(serverUrl,{
      transports: ['websocket'],
      secure: true,
      rejectUnauthorized: false
    });

    socket.value.on("connect", () => {
      isConnected.value = true;
      console.log("🚀 WebSocket Connected!");
    });

    socket.value.on("disconnect", () => {
      isConnected.value = false;
      console.log("❌ WebSocket Disconnected");
    });

    socket.value.on("connect_error", (err) => {
      console.error("🌐 Connection Error:", err.message);
      // Если видишь "xhr poll error", значит браузер блокирует HTTP внутри HTTPS
    });

    socket.value.on("processed_frame", (data: ArrayBuffer) => {
      const blob = new Blob([data], { type: "image/webp" });
      const newUrl = URL.createObjectURL(blob);
      processedImage.value = newUrl;
    });
  };

  const sendFrame = (payload: FramePayload) => {
    if (socket.value?.connected) {
      // volatile — кадр дропнется, если сеть не успевает. Это убирает лаги.
      socket.value.volatile.emit("video_frame", payload);
    }
  };

  return { connectToServer, sendFrame, processedImage, isConnected };
};