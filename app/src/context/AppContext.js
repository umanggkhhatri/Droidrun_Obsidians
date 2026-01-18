/**
 * App Context - Global state management
 */

import React, { createContext, useState, useCallback } from "react";

export const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [appState, setAppState] = useState({
    sessionId: null,
    imageUri: null,
    imageName: null,
    description: "",
    selectedPlatforms: ["instagram", "linkedin", "twitter", "threads"],
    platformPreviews: {},
    results: {},
    isLoading: false,
    loadingText: "Loading...",
  });

  const setSessionId = useCallback((sessionId) => {
    setAppState((prev) => ({ ...prev, sessionId }));
  }, []);

  const setImage = useCallback((uri, name) => {
    setAppState((prev) => ({ ...prev, imageUri: uri, imageName: name }));
  }, []);

  const setDescription = useCallback((description) => {
    setAppState((prev) => ({ ...prev, description }));
  }, []);

  const setSelectedPlatforms = useCallback((platforms) => {
    setAppState((prev) => ({ ...prev, selectedPlatforms: platforms }));
  }, []);

  const setPlatformPreviews = useCallback((previews) => {
    setAppState((prev) => ({ ...prev, platformPreviews: previews }));
  }, []);

  const setResults = useCallback((results) => {
    setAppState((prev) => ({ ...prev, results }));
  }, []);

  const setLoading = useCallback((isLoading, loadingText = "Loading...") => {
    setAppState((prev) => ({ ...prev, isLoading, loadingText }));
  }, []);

  const resetState = useCallback(() => {
    setAppState({
      sessionId: null,
      imageUri: null,
      imageName: null,
      description: "",
      selectedPlatforms: ["instagram", "linkedin", "twitter", "threads"],
      platformPreviews: {},
      results: {},
      isLoading: false,
      loadingText: "Loading...",
    });
  }, []);

  const value = {
    ...appState,
    setSessionId,
    setImage,
    setDescription,
    setSelectedPlatforms,
    setPlatformPreviews,
    setResults,
    setLoading,
    resetState,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};
