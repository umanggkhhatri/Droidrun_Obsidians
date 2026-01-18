/**
 * Common Components
 */

import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  View,
} from 'react-native';

// Primary Button
export const PrimaryButton = ({ title, onPress, disabled, loading, style }) => (
  <TouchableOpacity
    style={[styles.button, styles.primaryButton, disabled && styles.disabled, style]}
    onPress={onPress}
    disabled={disabled || loading}
  >
    {loading ? (
      <ActivityIndicator color="#ffffff" size="small" />
    ) : (
      <Text style={styles.buttonText}>{title}</Text>
    )}
  </TouchableOpacity>
);

// Secondary Button
export const SecondaryButton = ({ title, onPress, disabled, style }) => (
  <TouchableOpacity
    style={[styles.button, styles.secondaryButton, disabled && styles.disabled, style]}
    onPress={onPress}
    disabled={disabled}
  >
    <Text style={[styles.buttonText, { color: '#6366f1' }]}>{title}</Text>
  </TouchableOpacity>
);

// Success Button
export const SuccessButton = ({ title, onPress, disabled, loading, style }) => (
  <TouchableOpacity
    style={[styles.button, styles.successButton, disabled && styles.disabled, style]}
    onPress={onPress}
    disabled={disabled || loading}
  >
    {loading ? (
      <ActivityIndicator color="#ffffff" size="small" />
    ) : (
      <Text style={styles.buttonText}>{title}</Text>
    )}
  </TouchableOpacity>
);

// Platform Card
export const PlatformCard = ({
  platform,
  icon,
  selected,
  onPress,
  description,
}) => (
  <TouchableOpacity
    style={[styles.platformCard, selected && styles.platformCardSelected]}
    onPress={onPress}
  >
    <View style={styles.platformCardContent}>
      <Text style={styles.platformIcon}>{icon}</Text>
      <Text style={styles.platformName}>{platform}</Text>
      <Text style={styles.platformDesc}>{description}</Text>
      {selected && <Text style={styles.checkmark}>✓</Text>}
    </View>
  </TouchableOpacity>
);

// Loading Overlay
export const LoadingOverlay = ({ visible, message }) => {
  if (!visible) return null;

  return (
    <View style={styles.loadingOverlay}>
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#6366f1" />
        <Text style={styles.loadingText}>{message}</Text>
      </View>
    </View>
  );
};

// Toast Message
export const ToastMessage = ({ message, type = 'info' }) => {
  const backgroundColor =
    type === 'success'
      ? '#10b981'
      : type === 'error'
      ? '#ef4444'
      : '#3b82f6';

  return (
    <View style={[styles.toast, { backgroundColor }]}>
      <Text style={styles.toastText}>{message}</Text>
    </View>
  );
};

// Card Component
export const Card = ({ children, style }) => (
  <View style={[styles.card, style]}>
    {children}
  </View>
);

// Progress Step
export const ProgressStep = ({ stepNumber, label, completed, active }) => (
  <View style={styles.progressStepContainer}>
    <View
      style={[
        styles.stepNumber,
        completed && styles.stepNumberCompleted,
        active && styles.stepNumberActive,
      ]}
    >
      <Text
        style={[
          styles.stepNumberText,
          (completed || active) && { color: '#ffffff' },
        ]}
      >
        {completed ? '✓' : stepNumber}
      </Text>
    </View>
    <Text style={styles.stepLabel}>{label}</Text>
  </View>
);

const styles = StyleSheet.create({
  // Button Styles
  button: {
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 8,
  },
  primaryButton: {
    backgroundColor: '#6366f1',
  },
  secondaryButton: {
    backgroundColor: '#ffffff',
    borderWidth: 2,
    borderColor: '#e5e7eb',
  },
  successButton: {
    backgroundColor: '#10b981',
  },
  disabled: {
    opacity: 0.5,
  },
  buttonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
  },

  // Platform Card
  platformCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    marginVertical: 8,
    borderWidth: 2,
    borderColor: '#e5e7eb',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  platformCardSelected: {
    borderColor: '#6366f1',
    backgroundColor: '#f3f4f6',
  },
  platformCardContent: {
    flex: 1,
  },
  platformIcon: {
    fontSize: 24,
    marginBottom: 4,
  },
  platformName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  platformDesc: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 4,
  },
  checkmark: {
    fontSize: 20,
    color: '#10b981',
    fontWeight: 'bold',
  },

  // Loading Overlay
  loadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  loadingContainer: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 32,
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 14,
    color: '#6b7280',
  },

  // Toast
  toast: {
    backgroundColor: '#3b82f6',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
    marginVertical: 8,
  },
  toastText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '500',
  },

  // Card
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    marginVertical: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 3,
  },

  // Progress Step
  progressStepContainer: {
    alignItems: 'center',
    marginHorizontal: 8,
  },
  stepNumber: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#ffffff',
    borderWidth: 2,
    borderColor: '#e5e7eb',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  stepNumberCompleted: {
    backgroundColor: '#10b981',
    borderColor: '#10b981',
  },
  stepNumberActive: {
    backgroundColor: '#6366f1',
    borderColor: '#6366f1',
  },
  stepNumberText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#6b7280',
  },
  stepLabel: {
    fontSize: 12,
    fontWeight: '500',
    color: '#111827',
    textAlign: 'center',
    maxWidth: 70,
  },
});
