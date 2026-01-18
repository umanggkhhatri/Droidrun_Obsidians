import React, { useContext } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  SafeAreaView,
} from 'react-native';
import { AppContext } from '../context/AppContext';
import { PrimaryButton } from '../components';

export default function HomeScreen({ navigation }) {
  const { resetState } = useContext(AppContext);

  const startPosting = () => {
    resetState();
    navigation.navigate('UploadPhoto');
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerEmoji}>🚀</Text>
          <Text style={styles.title}>Social Media Automator</Text>
          <Text style={styles.subtitle}>Post to all platforms instantly</Text>
        </View>

        {/* Server Status */}
        {showServerWarning && (
          <View style={[styles.card, styles.warningCard]}>
            <Text style={styles.warningTitle}>⚠️ Server Connection</Text>
            <Text style={styles.warningText}>
              Status: {serverStatus ? '✓ Connected' : '✗ Not Connected'}
            </Text>
            <PrimaryButton
              title="Configure Server"
              onPress={configureServer}
              style={{ marginTop: 12 }}
            />
          </View>
        )}

        {/* Progress Overview */}
        <View style={styles.progressContainer}>
          <Text style={styles.sectionTitle}>📋 How it Works</Text>
          <View style={styles.progressSteps}>
            <ProgressStep stepNumber="1" label="Upload Photo" />
            <View style={styles.progressConnector} />
            <ProgressStep stepNumber="2" label="Write" />
            <View style={styles.progressConnector} />
            <ProgressStep stepNumber="3" label="Select" />
            <View style={styles.progressConnector} />
            <ProgressStep stepNumber="4" label="Post" />
          </View>
        </View>

        {/* Platforms Overview */}
        <View style={styles.platformsOverview}>
          <Text style={styles.sectionTitle}>📱 Supported Platforms</Text>
          <View style={styles.platformsGrid}>
            <PlatformCard
              platform="Instagram"
              icon="📷"
              description="2200 chars"
              selected={false}
              onPress={() => {}}
            />
            <PlatformCard
              platform="LinkedIn"
              icon="💼"
              description="3000 chars"
              selected={false}
              onPress={() => {}}
            />
            <PlatformCard
              platform="X (Twitter)"
              icon="𝕏"
              description="280 chars"
              selected={false}
              onPress={() => {}}
            />
            <PlatformCard
              platform="Threads"
              icon="🧵"
              description="500 chars"
              selected={false}
              onPress={() => {}}
            />
          </View>
        </View>

        {/* Features */}
        <View style={styles.featuresContainer}>
          <Text style={styles.sectionTitle}>✨ Features</Text>
          <Feature icon="📸" title="Easy Upload" description="Upload photos from your device" />
          <Feature icon="✍️" title="Smart Adaptation" description="Content optimized per platform" />
          <Feature icon="👁️" title="Preview" description="See how content looks everywhere" />
          <Feature icon="🚀" title="One-Click Post" description="Post to all platforms at once" />
        </View>

        {/* Start Button */}
        <PrimaryButton
          title="🚀 Start Creating Post"
          onPress={startPosting}
          style={styles.startButton}
        />

        {/* Info Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Powered by Droidrun • Automate your social media in seconds
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const Feature = ({ icon, title, description }) => (
  <View style={styles.feature}>
    <Text style={styles.featureIcon}>{icon}</Text>
    <View style={styles.featureContent}>
      <Text style={styles.featureTitle}>{title}</Text>
      <Text style={styles.featureDesc}>{description}</Text>
    </View>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  scrollContent: {
    paddingHorizontal: 16,
    paddingVertical: 24,
  },

  // Header
  header: {
    alignItems: 'center',
    marginBottom: 32,
    paddingTop: 16,
  },
  headerEmoji: {
    fontSize: 48,
    marginBottom: 12,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#6b7280',
  },

  // Card styles
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 3,
  },
  warningCard: {
    borderLeftWidth: 4,
    borderLeftColor: '#f59e0b',
    backgroundColor: 'rgba(245, 158, 11, 0.05)',
  },
  warningTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 8,
  },
  warningText: {
    fontSize: 14,
    color: '#6b7280',
  },

  // Progress Container
  progressContainer: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 16,
  },
  progressSteps: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 12,
  },
  progressConnector: {
    width: 2,
    height: 50,
    backgroundColor: '#e5e7eb',
    marginHorizontal: 4,
  },

  // Platforms Overview
  platformsOverview: {
    marginBottom: 32,
  },
  platformsGrid: {
    gap: 8,
  },

  // Features
  featuresContainer: {
    marginBottom: 32,
  },
  feature: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  featureIcon: {
    fontSize: 28,
    marginRight: 12,
  },
  featureContent: {
    flex: 1,
  },
  featureTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 4,
  },
  featureDesc: {
    fontSize: 13,
    color: '#6b7280',
  },

  // Start Button
  startButton: {
    marginBottom: 24,
    paddingVertical: 16,
  },

  // Footer
  footer: {
    alignItems: 'center',
    paddingVertical: 16,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  footerText: {
    fontSize: 12,
    color: '#9ca3af',
    textAlign: 'center',
  },
});
