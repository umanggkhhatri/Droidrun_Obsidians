/**
 * Results Screen - Shows posting results
 */

import React, { useContext, useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Alert,
} from 'react-native';
import { AppContext } from '../context/AppContext';
import { PrimaryButton, LoadingOverlay } from '../components';
import ApiService from '../services/ApiService';

export default function ResultsScreen({ navigation }) {
  const {
    sessionId,
    description,
    selectedPlatforms,
    setResults,
    setLoading,
    isLoading,
    resetState,
  } = useContext(AppContext);

  const [results, setLocalResults] = useState({});
  const [posting, setPosting] = useState(true);

  useEffect(() => {
    postContent();
  }, []);

  const postContent = async () => {
    try {
      setPosting(true);
      setLoading(true, 'Posting to platforms...');

      const response = await ApiService.postContent(
        sessionId,
        description,
        selectedPlatforms
      );

      setLocalResults(response.results);
      setResults(response.results);
      setLoading(false);
      setPosting(false);
    } catch (error) {
      setLoading(false);
      setPosting(false);
      Alert.alert('Error', error.message || 'Failed to post content', [
        { text: 'Retry', onPress: postContent },
        { text: 'Back', onPress: () => navigation.goBack() },
      ]);
    }
  };

  const handlePostAgain = () => {
    resetState();
    navigation.navigate('Home');
  };

  const platformIcons = {
    instagram: '📷',
    linkedin: '💼',
    x: '𝕏',
    threads: '🧵',
  };

  const platformNames = {
    instagram: 'Instagram',
    linkedin: 'LinkedIn',
    x: 'X (Twitter)',
    threads: 'Threads',
  };

  const successCount = Object.values(results).filter((r) => r.success).length;
  const failureCount = Object.values(results).filter((r) => !r.success).length;

  if (posting) {
    return (
      <SafeAreaView style={styles.container}>
        <LoadingOverlay visible={true} message="Posting to platforms..." />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={styles.content}>
          {/* Summary */}
          <View
            style={[
              styles.summaryCard,
              successCount > 0 ? styles.successSummary : styles.errorSummary,
            ]}
          >
            <Text style={styles.summaryIcon}>
              {successCount === selectedPlatforms.length ? '✅' : '⚠️'}
            </Text>
            <Text style={styles.summaryTitle}>
              {successCount === selectedPlatforms.length
                ? 'All Posted! 🎉'
                : 'Posting Complete'}
            </Text>
            <View style={styles.statsRow}>
              <View style={styles.statItem}>
                <Text style={styles.statValue}>{successCount}</Text>
                <Text style={styles.statLabel}>Success</Text>
              </View>
              {failureCount > 0 && (
                <View style={styles.statItem}>
                  <Text style={[styles.statValue, styles.failureText]}>{failureCount}</Text>
                  <Text style={styles.statLabel}>Failed</Text>
                </View>
              )}
            </View>
          </View>

          {/* Results List */}
          <View style={styles.resultsContainer}>
            <Text style={styles.resultsTitle}>📊 Results</Text>

            {selectedPlatforms.map((platform) => {
              const result = results[platform];
              if (!result) return null;

              return (
                <ResultCard
                  key={platform}
                  platform={platform}
                  result={result}
                  icon={platformIcons[platform]}
                  name={platformNames[platform]}
                />
              );
            })}
          </View>

          {/* Tips */}
          <View style={styles.tipsSection}>
            <Text style={styles.tipsTitle}>💡 Next Steps</Text>
            <Text style={styles.tipText}>✓ Check your posts on each platform</Text>
            <Text style={styles.tipText}>✓ Engage with comments and likes</Text>
            <Text style={styles.tipText}>✓ Track performance metrics</Text>
            <Text style={styles.tipText}>✓ Share the app with friends!</Text>
          </View>

          {/* Action Buttons */}
          <PrimaryButton
            title="🔄 Post Another"
            onPress={handlePostAgain}
            style={styles.postAgainButton}
          />
        </View>
      </ScrollView>

      <LoadingOverlay visible={isLoading} message="Posting to platforms..." />
    </SafeAreaView>
  );
}

const ResultCard = ({ platform, result, icon, name }) => (
  <View style={[styles.resultCard, result.success && styles.resultSuccess, !result.success && styles.resultError]}>
    <View style={styles.resultHeader}>
      <Text style={styles.resultIcon}>{icon}</Text>
      <View style={styles.resultInfo}>
        <Text style={styles.resultPlatform}>{name}</Text>
        <Text
          style={[
            styles.resultStatus,
            { color: result.success ? '#10b981' : '#ef4444' },
          ]}
        >
          {result.success ? '✓ Posted' : '✗ Failed'}
        </Text>
      </View>
    </View>

    <View style={styles.resultBody}>
      <Text style={styles.resultReason}>
        {result.reason || (result.success ? 'Posted successfully' : 'An error occurred')}
      </Text>
      {result.steps && (
        <Text style={styles.resultMeta}>
          Steps executed: {result.steps}
        </Text>
      )}
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
    paddingVertical: 16,
  },
  content: {
    flex: 1,
  },

  // Summary Card
  summaryCard: {
    borderRadius: 12,
    padding: 24,
    marginBottom: 24,
    alignItems: 'center',
  },
  successSummary: {
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    borderWidth: 2,
    borderColor: '#10b981',
  },
  errorSummary: {
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
    borderWidth: 2,
    borderColor: '#f59e0b',
  },
  summaryIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  summaryTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 16,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 24,
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 28,
    fontWeight: '700',
    color: '#10b981',
  },
  failureText: {
    color: '#ef4444',
  },
  statLabel: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 4,
  },

  // Results Container
  resultsContainer: {
    marginBottom: 24,
  },
  resultsTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 12,
  },

  // Result Card
  resultCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderLeftWidth: 4,
  },
  resultSuccess: {
    borderLeftColor: '#10b981',
  },
  resultError: {
    borderLeftColor: '#ef4444',
  },

  resultHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  resultIcon: {
    fontSize: 28,
    marginRight: 12,
  },
  resultInfo: {
    flex: 1,
  },
  resultPlatform: {
    fontSize: 15,
    fontWeight: '600',
    color: '#111827',
  },
  resultStatus: {
    fontSize: 12,
    marginTop: 2,
    fontWeight: '600',
  },

  resultBody: {
    paddingLeft: 40,
  },
  resultReason: {
    fontSize: 13,
    color: '#374151',
    marginBottom: 4,
  },
  resultMeta: {
    fontSize: 11,
    color: '#9ca3af',
    marginTop: 4,
  },

  // Tips Section
  tipsSection: {
    backgroundColor: '#ffffff',
    borderRadius: 8,
    padding: 16,
    marginBottom: 24,
    borderLeftWidth: 4,
    borderLeftColor: '#3b82f6',
  },
  tipsTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 8,
  },
  tipText: {
    fontSize: 13,
    color: '#6b7280',
    marginBottom: 6,
    lineHeight: 18,
  },

  // Post Again Button
  postAgainButton: {
    paddingVertical: 14,
    marginTop: 8,
  },
});
