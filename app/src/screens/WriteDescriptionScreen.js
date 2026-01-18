/**
 * Write Description Screen
 */

import React, { useContext, useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  TextInput,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { AppContext } from "../context/AppContext";
import { PrimaryButton, SecondaryButton } from "../components";
import ApiService from "../services/ApiService";

export default function WriteDescriptionScreen({ navigation }) {
  const { description, setDescription } = useContext(AppContext);
  const [localDescription, setLocalDescription] = useState(description);
  const [charCount, setCharCount] = useState(description.length);
  const MAX_CHARS = 5000;

  useEffect(() => {
    setCharCount(localDescription.length);
  }, [localDescription]);

  const handleDescriptionChange = (text) => {
    setLocalDescription(text);
  };

  const handleContinue = async () => {
    if (!localDescription.trim()) {
      Alert.alert("Error", "Please write a description");
      return;
    }

    if (localDescription.length > MAX_CHARS) {
      Alert.alert(
        "Error",
        `Description is too long. Maximum: ${MAX_CHARS} characters`,
      );
      return;
    }

    try {
      setDescription(localDescription);
      navigation.navigate("SelectPlatforms");
    } catch (error) {
      Alert.alert("Error", error.message || "Failed to validate description");
    }
  };

  const getCharCountColor = () => {
    const percentage = charCount / MAX_CHARS;
    if (percentage < 0.8) return "#6b7280";
    if (percentage < 0.95) return "#f59e0b";
    return "#ef4444";
  };

  const handleInsertTemplate = (template) => {
    setLocalDescription((prev) => prev + template);
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={{ flex: 1 }}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.content}>
            {/* Instruction */}
            <View style={styles.instructionCard}>
              <Text style={styles.instructionIcon}>✍️</Text>
              <Text style={styles.instructionTitle}>
                Write Your Description
              </Text>
              <Text style={styles.instructionText}>
                Share your thoughts! Content will be automatically adapted for
                each platform.
              </Text>
            </View>

            {/* Text Input */}
            <TextInput
              style={styles.descriptionInput}
              placeholder="Write your description here..."
              placeholderTextColor="#d1d5db"
              multiline
              maxLength={MAX_CHARS}
              value={localDescription}
              onChangeText={handleDescriptionChange}
              textAlignVertical="top"
            />

            {/* Character Count */}
            <View style={styles.charCountContainer}>
              <Text style={[styles.charCount, { color: getCharCountColor() }]}>
                {charCount} / {MAX_CHARS} characters
              </Text>
              {charCount > MAX_CHARS * 0.9 && (
                <Text style={styles.charWarning}>
                  {charCount > MAX_CHARS
                    ? "❌ Too long!"
                    : "⚠️ Getting close to limit"}
                </Text>
              )}
            </View>

            {/* Templates Section */}
            <View style={styles.templatesSection}>
              <Text style={styles.sectionTitle}>📝 Quick Templates</Text>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                style={styles.templateScroll}
              >
                <TemplateButton
                  text="Product Launch 🚀"
                  onPress={() =>
                    handleInsertTemplate(
                      "\n\n🚀 Excited to announce our new product! Swipe to see the magic.",
                    )
                  }
                />
                <TemplateButton
                  text="Event Update 🎉"
                  onPress={() =>
                    handleInsertTemplate(
                      "\n\n🎉 Amazing things happening today! Join us! #event",
                    )
                  }
                />
                <TemplateButton
                  text="Content Share 📚"
                  onPress={() =>
                    handleInsertTemplate(
                      "\n\n📚 Just discovered this gem! Check it out. #learning #growth",
                    )
                  }
                />
                <TemplateButton
                  text="Tips & Tricks 💡"
                  onPress={() =>
                    handleInsertTemplate(
                      "\n\n💡 Quick tip: This changed everything! Try it! #tips",
                    )
                  }
                />
              </ScrollView>
            </View>

            {/* Tips Section */}
            <View style={styles.tipsSection}>
              <Text style={styles.sectionTitle}>💬 Tips</Text>
              <Text style={styles.tipText}>✓ Be authentic and engaging</Text>
              <Text style={styles.tipText}>✓ Use emojis to stand out</Text>
              <Text style={styles.tipText}>✓ Include a call-to-action</Text>
              <Text style={styles.tipText}>✓ Keep mobile viewers in mind</Text>
            </View>

            {/* Action Buttons */}
            <View style={styles.buttonContainer}>
              <SecondaryButton
                title="⬅️ Back"
                onPress={() => navigation.goBack()}
              />
              <PrimaryButton
                title="Next ➜"
                onPress={handleContinue}
                disabled={!localDescription.trim() || charCount > MAX_CHARS}
              />
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const TemplateButton = ({ text, onPress }) => (
  <PrimaryButton title={text} onPress={onPress} style={styles.templateButton} />
);

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

  // Text Input
  descriptionInput: {
    backgroundColor: "#ffffff",
    borderRadius: 12,
    borderWidth: 2,
    borderColor: "#e5e7eb",
    padding: 16,
    fontSize: 16,
    color: "#111827",
    minHeight: 200,
    maxHeight: 300,
    marginBottom: 12,
    fontFamily: Platform.OS === "ios" ? "System" : "Roboto",
  },

  // Character Count
  charCountContainer: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 4,
    marginBottom: 20,
  },
  charCount: {
    fontSize: 13,
    fontWeight: "600",
  },
  charWarning: {
    fontSize: 12,
    color: "#f59e0b",
    fontWeight: "600",
  },

  // Templates Section
  templatesSection: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#111827",
    marginBottom: 12,
  },
  templateScroll: {
    marginHorizontal: -16,
    paddingHorizontal: 16,
  },
  templateButton: {
    marginRight: 12,
    marginVertical: 0,
    paddingVertical: 10,
    paddingHorizontal: 14,
    minWidth: 130,
  },

  // Tips Section
  tipsSection: {
    backgroundColor: "#ffffff",
    borderRadius: 8,
    padding: 16,
    marginBottom: 24,
    borderLeftWidth: 4,
    borderLeftColor: "#10b981",
  },
  tipText: {
    fontSize: 13,
    color: "#6b7280",
    marginBottom: 8,
    lineHeight: 18,
  },

  // Buttons
  buttonContainer: {
    flexDirection: "row",
    gap: 12,
    marginTop: 8,
  },
});
