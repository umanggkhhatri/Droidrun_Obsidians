/**
 * Upload Photo Screen
 */

import React, { useContext, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  SafeAreaView,
  ScrollView,
  Alert,
  ActivityIndicator,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { AppContext } from "../context/AppContext";
import { PrimaryButton, SecondaryButton, LoadingOverlay } from "../components";
import ApiService from "../services/ApiService";

export default function UploadPhotoScreen({ navigation }) {
  const { imageUri, imageName, setImage, setSessionId, setLoading, isLoading } =
    useContext(AppContext);

  const [selectedImage, setSelectedImage] = useState(imageUri);
  const [selectedImageName, setSelectedImageName] = useState(imageName);
  const [uploading, setUploading] = useState(false);

  const pickImage = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 3],
        quality: 1,
      });

      if (!result.canceled) {
        const asset = result.assets[0];
        setSelectedImage(asset.uri);
        setSelectedImageName(asset.fileName || "image.jpg");
      }
    } catch (error) {
      Alert.alert("Error", "Failed to pick image");
    }
  };

  const takePhoto = async () => {
    try {
      const result = await ImagePicker.launchCameraAsync({
        allowsEditing: true,
        aspect: [4, 3],
        quality: 1,
      });

      if (!result.canceled) {
        const asset = result.assets[0];
        setSelectedImage(asset.uri);
        setSelectedImageName(asset.fileName || "photo.jpg");
      }
    } catch (error) {
      Alert.alert("Error", "Failed to take photo");
    }
  };

  const uploadImage = async () => {
    if (!selectedImage) {
      Alert.alert("Error", "Please select an image first");
      return;
    }

    try {
      setUploading(true);
      setLoading(true, "Processing photo...");

      // Store image locally - no backend upload needed
      setImage(selectedImage, selectedImageName);

      Alert.alert("Success", "Photo ready! 📸", [
        {
          text: "Next",
          onPress: () => navigation.navigate("WriteDescription"),
        },
      ]);
    } catch (error) {
      Alert.alert("Error", error.message || "Failed to process image");
    } finally {
      setUploading(false);
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.content}>
          {/* Instruction */}
          <View style={styles.instructionCard}>
            <Text style={styles.instructionIcon}>📸</Text>
            <Text style={styles.instructionTitle}>Upload Your Photo</Text>
            <Text style={styles.instructionText}>
              Choose a photo from your gallery or take a new one
            </Text>
          </View>

          {/* Image Preview or Placeholder */}
          <View style={styles.previewContainer}>
            {selectedImage ? (
              <Image
                source={{ uri: selectedImage }}
                style={styles.previewImage}
                resizeMode="cover"
              />
            ) : (
              <View style={styles.placeholderImage}>
                <Text style={styles.placeholderIcon}>🖼️</Text>
                <Text style={styles.placeholderText}>No image selected</Text>
              </View>
            )}
          </View>

          {/* Image Info */}
          {selectedImage && (
            <View style={styles.imageInfo}>
              <Text style={styles.imageInfoLabel}>Selected File:</Text>
              <Text style={styles.imageInfoValue}>{selectedImageName}</Text>
            </View>
          )}

          {/* Action Buttons */}
          <View style={styles.buttonGroup}>
            <View style={styles.buttonRow}>
              <PrimaryButton
                title="📷 Camera"
                onPress={takePhoto}
                style={styles.halfButton}
              />
              <PrimaryButton
                title="🖼️ Gallery"
                onPress={pickImage}
                style={styles.halfButton}
              />
            </View>

            {selectedImage && (
              <SecondaryButton
                title="🔄 Change Photo"
                onPress={() => {
                  setSelectedImage(null);
                  setSelectedImageName(null);
                }}
                style={styles.fullButton}
              />
            )}
          </View>

          {/* Upload Button */}
          {selectedImage && (
            <PrimaryButton
              title={uploading ? "Uploading..." : "⬆️ Upload Photo"}
              onPress={uploadImage}
              disabled={uploading}
              loading={uploading}
              style={styles.uploadButton}
            />
          )}

          {/* Info */}
          <View style={styles.infoSection}>
            <Text style={styles.infoTitle}>ℹ️ Tips</Text>
            <Text style={styles.infoText}>
              • Use high-quality images for best results
            </Text>
            <Text style={styles.infoText}>
              • Supported formats: JPG, PNG, GIF, WebP
            </Text>
            <Text style={styles.infoText}>• Maximum file size: 50MB</Text>
          </View>
        </View>
      </ScrollView>

      <LoadingOverlay visible={isLoading} message="Uploading photo..." />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f9fafb",
  },
  scrollContent: {
    paddingHorizontal: 16,
    paddingVertical: 16,
  },
  content: {
    flex: 1,
  },

  // Instruction Card
  instructionCard: {
    backgroundColor:
      "linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)",
    borderRadius: 12,
    padding: 20,
    marginBottom: 24,
    alignItems: "center",
  },
  instructionIcon: {
    fontSize: 40,
    marginBottom: 12,
  },
  instructionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#111827",
    marginBottom: 8,
  },
  instructionText: {
    fontSize: 14,
    color: "#6b7280",
    textAlign: "center",
  },

  // Preview Container
  previewContainer: {
    backgroundColor: "#ffffff",
    borderRadius: 12,
    overflow: "hidden",
    marginBottom: 24,
    height: 320,
    borderWidth: 2,
    borderColor: "#e5e7eb",
  },
  previewImage: {
    width: "100%",
    height: "100%",
  },
  placeholderImage: {
    width: "100%",
    height: "100%",
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#f3f4f6",
  },
  placeholderIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  placeholderText: {
    fontSize: 14,
    color: "#9ca3af",
  },

  // Image Info
  imageInfo: {
    backgroundColor: "#ffffff",
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: "#10b981",
  },
  imageInfoLabel: {
    fontSize: 12,
    color: "#6b7280",
    marginBottom: 4,
  },
  imageInfoValue: {
    fontSize: 14,
    fontWeight: "600",
    color: "#111827",
  },

  // Button Styles
  buttonGroup: {
    marginBottom: 20,
  },
  buttonRow: {
    flexDirection: "row",
    gap: 12,
  },
  halfButton: {
    flex: 1,
    marginVertical: 0,
  },
  fullButton: {
    marginVertical: 8,
  },
  uploadButton: {
    marginBottom: 24,
    paddingVertical: 14,
  },

  // Info Section
  infoSection: {
    backgroundColor: "#ffffff",
    borderRadius: 8,
    padding: 16,
    borderLeftWidth: 4,
    borderLeftColor: "#3b82f6",
  },
  infoTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "#111827",
    marginBottom: 8,
  },
  infoText: {
    fontSize: 13,
    color: "#6b7280",
    lineHeight: 20,
    marginBottom: 4,
  },
});
