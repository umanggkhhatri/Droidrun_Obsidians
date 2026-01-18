/**
 * API Service - Handles all backend communication
 */

import axios from "axios";
import * as FileSystem from "expo-file-system";

// Configure API endpoint - adjust this to your Flask server
// IMPORTANT: Change 192.168.1.X to your machine's local IP address
// Find it with: ifconfig | grep "inet " (on Mac)
const API_BASE_URL = "http://192.168.1.100:5000"; // Change IP + port here

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
});

export const ApiService = {
  /**
   * Post content to selected platforms (main endpoint)
   */
  postContent: async (text, links, media, platforms) => {
    try {
      const formData = new FormData();
      formData.append("text", text);
      formData.append("links", links);
      formData.append("platforms", JSON.stringify(platforms));

      // Attach media files
      if (media && media.length > 0) {
        for (let i = 0; i < media.length; i++) {
          const fileUri = media[i];
          const fileName = fileUri.split("/").pop();

          const response = await FileSystem.readAsStringAsync(fileUri, {
            encoding: FileSystem.EncodingType.Base64,
          });

          formData.append("media", {
            uri: fileUri,
            name: fileName,
            type: fileName.endsWith(".mp4") ? "video/mp4" : "image/jpeg",
          });
        }
      }

      const postResponse = await api.post("/api/post", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      return postResponse.data;
    } catch (error) {
      console.error("Post error:", error);
      throw new Error(
        error.response?.data?.error ||
          error.message ||
          "Failed to post content",
      );
    }
  },

  /**
   * Health check
   */
  healthCheck: async () => {
    try {
      const response = await api.get("/api/health");
      return response.status === 200;
    } catch (error) {
      console.error("Health check failed:", error);
      return false;
    }
  },

  /**
   * Set API base URL (for runtime configuration)
   */
  setBaseURL: (url) => {
    api.defaults.baseURL = url;
  },
};

export default ApiService;
