/**
 * Select Platforms Screen
 */

import React, { useContext, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Alert,
  TouchableOpacity,
} from 'react-native';
import { AppContext } from '../context/AppContext';
import { PrimaryButton, SecondaryButton, PlatformCard } from '../components';

export default function SelectPlatformsScreen({ navigation }) {
  const { selectedPlatforms, setSelectedPlatforms } = useContext(AppContext);
  const [localSelectedPlatforms, setLocalSelectedPlatforms] = useState(selectedPlatforms);

  const platformsList = [
    {
      id: 'instagram',
      name: 'Instagram',
      icon: '📷',
      description: 'Image-focused, 2200 characters',
      maxChars: 2200,
    },
    {
      id: 'linkedin',
      name: 'LinkedIn',
      icon: '💼',
      description: 'Professional network, 3000 characters',
      maxChars: 3000,
    },
    {
      id: 'x',
      name: 'X (Twitter)',
      icon: '𝕏',
      description: 'Fast-paced, 280 characters',
      maxChars: 280,
    },
    {
      id: 'threads',
      name: 'Threads',
      icon: '🧵',
      description: 'Conversational, 500 characters',
      maxChars: 500,
    },
  ];

  const togglePlatform = (platformId) => {
    setLocalSelectedPlatforms((prev) => {
      if (prev.includes(platformId)) {
        const updated = prev.filter((p) => p !== platformId);
        // Ensure at least one platform is selected
        return updated.length > 0 ? updated : prev;
      } else {
        return [...prev, platformId];
      }
    });
  };

  const handleContinue = () => {
    if (localSelectedPlatforms.length === 0) {
      Alert.alert('Error', 'Please select at least one platform');
      return;
    }

    setSelectedPlatforms(localSelectedPlatforms);
    navigation.navigate('Preview');
  };

  const selectAll = () => {
    setLocalSelectedPlatforms(platformsList.map((p) => p.id));
  };

  const deselectAll = () => {
    // Keep at least one selected
    if (localSelectedPlatforms.length > 1) {
      setLocalSelectedPlatforms([localSelectedPlatforms[0]]);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={styles.content}>
          {/* Instruction */}
          <View style={styles.instructionCard}>
            <Text style={styles.instructionIcon}>🎯</Text>
            <Text style={styles.instructionTitle}>Select Platforms</Text>
            <Text style={styles.instructionText}>
              Choose where to post your content. You can select multiple platforms.
            </Text>
          </View>

          {/* Quick Actions */}
          <View style={styles.quickActionsContainer}>
            <TouchableOpacity
              style={[styles.quickActionButton, styles.selectAllButton]}
              onPress={selectAll}
            >
              <Text style={styles.quickActionText}>✓ Select All</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.quickActionButton, styles.deselectButton]}
              onPress={deselectAll}
            >
              <Text style={styles.quickActionText}>✗ Deselect</Text>
            </TouchableOpacity>
          </View>

          {/* Platforms List */}
          <View style={styles.platformsList}>
            {platformsList.map((platform) => (
              <TouchableOpacity
                key={platform.id}
                onPress={() => togglePlatform(platform.id)}
                activeOpacity={0.7}
              >
                <PlatformCard
                  platform={platform.name}
                  icon={platform.icon}
                  description={platform.description}
                  selected={localSelectedPlatforms.includes(platform.id)}
                  onPress={() => togglePlatform(platform.id)}
                />
              </TouchableOpacity>
            ))}
          </View>

          {/* Stats */}
          <View style={styles.statsContainer}>
            <View style={styles.statCard}>
              <Text style={styles.statNumber}>{localSelectedPlatforms.length}</Text>
              <Text style={styles.statLabel}>Platforms Selected</Text>
            </View>
          </View>

          {/* Info */}
          <View style={styles.infoSection}>
            <Text style={styles.infoTitle}>💡 Did you know?</Text>
            <Text style={styles.infoText}>
              Your description will be automatically adapted to fit each platform's character limit
              and style guidelines. You'll see a preview next!
            </Text>
          </View>

          {/* Action Buttons */}
          <View style={styles.buttonContainer}>
            <SecondaryButton title="⬅️ Back" onPress={() => navigation.goBack()} />
            <PrimaryButton
              title="Next ➜"
              onPress={handleContinue}
              disabled={localSelectedPlatforms.length === 0}
            />
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
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
    backgroundColor: 'rgba(99, 102, 241, 0.1)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    alignItems: 'center',
  },
  instructionIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  instructionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 6,
  },
  instructionText: {
    fontSize: 13,
    color: '#6b7280',
    textAlign: 'center',
  },

  // Quick Actions
  quickActionsContainer: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  quickActionButton: {
    flex: 1,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  selectAllButton: {
    backgroundColor: '#10b981',
  },
  deselectButton: {
    backgroundColor: '#ef4444',
  },
  quickActionText: {
    color: '#ffffff',
    fontWeight: '600',
    fontSize: 13,
  },

  // Platforms List
  platformsList: {
    marginBottom: 20,
    gap: 8,
  },

  // Stats
  statsContainer: {
    marginBottom: 20,
  },
  statCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderLeftWidth: 4,
    borderLeftColor: '#6366f1',
  },
  statNumber: {
    fontSize: 28,
    fontWeight: '700',
    color: '#6366f1',
  },
  statLabel: {
    fontSize: 13,
    color: '#6b7280',
    marginTop: 4,
  },

  // Info Section
  infoSection: {
    backgroundColor: '#ffffff',
    borderRadius: 8,
    padding: 16,
    marginBottom: 24,
    borderLeftWidth: 4,
    borderLeftColor: '#3b82f6',
  },
  infoTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 8,
  },
  infoText: {
    fontSize: 13,
    color: '#6b7280',
    lineHeight: 20,
  },

  // Buttons
  buttonContainer: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 8,
  },
});
