/**
 * Preview Screen
 */

import React, { useContext, useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Alert,
} from "react-native";
import { AppContext } from "../context/AppContext";
import { PrimaryButton, SecondaryButton, LoadingOverlay } from "../components";
import ApiService from "../services/ApiService";

export default function PreviewScreen({ navigation }) {
  const {
    description,
    selectedPlatforms,
    setPlatformPreviews,
    setLoading,
    isLoading,
  } = useContext(AppContext);

  const [previews, setPreviews] = useState({});
  const [localLoading, setLocalLoading] = useState(true);

  useEffect(() => {
    generatePreviews();
  }, []);

  const generatePreviews = async () => {
    try {
      // Local preview generation without server call
      const localPreviews = {};
      selectedPlatforms.forEach((platform) => {
        localPreviews[platform] = {
          text: description,
          platform: platform,
        };
      });
      setPreviews(localPreviews);
      setPlatformPreviews(localPreviews);
      setLocalLoading(false);
    } catch (error) {
      setLocalLoading(false);
      Alert.alert("Error", error.message || "Failed to generate preview");
      navigation.goBack();
    }
  };

  const handlePost = () => {
    navigation.navigate("Results");
  };

  if (localLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <LoadingOverlay visible={true} message="Generating preview..." />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.content}>
          {/* Instruction */}
          <View style={styles.instructionCard}>
            <Text style={styles.instructionIcon}>👁️</Text>
            <Text style={styles.instructionTitle}>Content Preview</Text>
            <Text style={styles.instructionText}>
              See how your content looks on each platform
            </Text>
          </View>

          {/* Previews */}
          <View style={styles.previewsContainer}>
            {selectedPlatforms.map((platform) => {
              const preview = previews[platform];
              if (!preview) return null;

              return (
                <PreviewCard
                  key={platform}
                  platform={platform}
                  preview={preview}
                />
              );
            })}
          </View>

          {/* Tips */}
          <View style={styles.tipsSection}>
            <Text style={styles.tipsTitle}>✨ Optimization Tips</Text>
            <Text style={styles.tipText}>
              • Instagram: Perfect for visual storytelling with emojis
            </Text>
            <Text style={styles.tipText}>
              • LinkedIn: Professional tone, focus on value
            </Text>
            <Text style={styles.tipText}>
              • X: Concise and punchy, perfect for virality
            </Text>
            <Text style={styles.tipText}>
              • Threads: Conversational, great for discussions
            </Text>
          </View>

          {/* Action Buttons */}
          <View style={styles.buttonContainer}>
            <SecondaryButton
              title="⬅️ Back"
              onPress={() => navigation.goBack()}
            />
            <PrimaryButton title="🚀 Post Now" onPress={handlePost} />
          </View>
        </View>
      </ScrollView>

      <LoadingOverlay visible={isLoading} message="Generating preview..." />
    </SafeAreaView>
  );
}

const PreviewCard = ({ platform, preview }) => {
  const platformIcons = {
    instagram: "📷",
    linkedin: "💼",
    x: "𝕏",
    threads: "🧵",
  };

  const platformNames = {
    instagram: "Instagram",
    linkedin: "LinkedIn",
    x: "X (Twitter)",
    threads: "Threads",
  };

  const platformColors = {
    instagram: "#E1306C",
    linkedin: "#0077B5",
    x: "#000000",
    threads: "#000000",
  };

  return (
    <View style={styles.previewCard}>
      <View style={styles.previewHeader}>
        <Text style={styles.previewIcon}>{platformIcons[platform]}</Text>
        <View style={styles.previewHeaderInfo}>
          <Text style={styles.previewPlatform}>{platformNames[platform]}</Text>
          <Text
            style={[
              styles.previewStatus,
              { color: preview.fits ? "#10b981" : "#ef4444" },
            ]}
          >
            {preview.fits ? "✓ Fits" : "⚠️ Too long"}
          </Text>
        </View>
      </View>

      <View style={styles.previewContent}>
        <Text style={styles.previewText} numberOfLines={6}>
          {preview.content}
        </Text>
      </View>

      <View style={styles.previewMeta}>
        <Text style={styles.metaText}>
          {preview.length} / {preview.max_length} characters
        </Text>
        {!preview.fits && (
          <Text style={styles.metaWarning}>
            {preview.length - preview.max_length} chars over
          </Text>
        )}
      </View>
    </View>
  );
};

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
    backgroundColor: "rgba(99, 102, 241, 0.1)",
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    alignItems: "center",
  },
  instructionIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  instructionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#111827",
    marginBottom: 6,
  },
  instructionText: {
    fontSize: 13,
    color: "#6b7280",
    textAlign: "center",
  },

  // Previews Container
  previewsContainer: {
    marginBottom: 20,
    gap: 12,
  },

  // Preview Card
  previewCard: {
    backgroundColor: "#ffffff",
    borderRadius: 12,
    overflow: "hidden",
    borderWidth: 2,
    borderColor: "#e5e7eb",
  },

  previewHeader: {
    flexDirection: "row",
    alignItems: "center",
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
    backgroundColor: "#f9fafb",
  },
  previewIcon: {
    fontSize: 24,
    marginRight: 12,
  },
  previewHeaderInfo: {
    flex: 1,
  },
  previewPlatform: {
    fontSize: 15,
    fontWeight: "600",
    color: "#111827",
  },
  previewStatus: {
    fontSize: 12,
    marginTop: 2,
    fontWeight: "500",
  },

  previewContent: {
    padding: 12,
    minHeight: 80,
    justifyContent: "center",
  },
  previewText: {
    fontSize: 13,
    color: "#374151",
    lineHeight: 18,
  },

  previewMeta: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: "#f9fafb",
    borderTopWidth: 1,
    borderTopColor: "#e5e7eb",
  },
  metaText: {
    fontSize: 12,
    color: "#6b7280",
    fontWeight: "500",
  },
  metaWarning: {
    fontSize: 12,
    color: "#ef4444",
    fontWeight: "600",
    marginTop: 2,
  },

  // Tips Section
  tipsSection: {
    backgroundColor: "#ffffff",
    borderRadius: 8,
    padding: 16,
    marginBottom: 24,
    borderLeftWidth: 4,
    borderLeftColor: "#f59e0b",
  },
  tipsTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: "#111827",
    marginBottom: 8,
  },
  tipText: {
    fontSize: 12,
    color: "#6b7280",
    marginBottom: 6,
    lineHeight: 16,
  },

  // Buttons
  buttonContainer: {
    flexDirection: "row",
    gap: 12,
    marginTop: 8,
  },
});
