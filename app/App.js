import React, { useState } from "react";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { GestureHandlerRootView } from "react-native-gesture-handler";

// Screens
import HomeScreen from "./src/screens/HomeScreen";
import UploadPhotoScreen from "./src/screens/UploadPhotoScreen";
import WriteDescriptionScreen from "./src/screens/WriteDescriptionScreen";
import SelectPlatformsScreen from "./src/screens/SelectPlatformsScreen";
import PreviewScreen from "./src/screens/PreviewScreen";
import ResultsScreen from "./src/screens/ResultsScreen";

// Context
import { AppProvider } from "./src/context/AppContext";

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <AppProvider>
        <NavigationContainer>
          <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
          <Stack.Navigator
            screenOptions={{
              headerShown: true,
              headerStyle: {
                backgroundColor: "#34C759",
              },
              headerTintColor: "#ffffff",
              headerTitleStyle: {
                fontWeight: "700",
                fontSize: 18,
              },
              cardStyle: {
                backgroundColor: "#f9fafb",
              },
            }}
          >
            <Stack.Screen
              name="Home"
              component={HomeScreen}
              options={{
                headerShown: false,
              }}
            />
            <Stack.Screen
              name="UploadPhoto"
              component={UploadPhotoScreen}
              options={{
                title: "📸 Upload Photo",
                headerBackTitle: "Back",
              }}
            />
            <Stack.Screen
              name="WriteDescription"
              component={WriteDescriptionScreen}
              options={{
                title: "✍️ Write Description",
                headerBackTitle: "Back",
              }}
            />
            <Stack.Screen
              name="SelectPlatforms"
              component={SelectPlatformsScreen}
              options={{
                title: "🎯 Select Platforms",
                headerBackTitle: "Back",
              }}
            />
            <Stack.Screen
              name="Preview"
              component={PreviewScreen}
              options={{
                title: "👁️ Preview",
                headerBackTitle: "Back",
              }}
            />
            <Stack.Screen
              name="Results"
              component={ResultsScreen}
              options={{
                title: "📊 Results",
                headerLeft: null,
              }}
            />
          </Stack.Navigator>
        </NavigationContainer>
      </AppProvider>
    </GestureHandlerRootView>
  );
}
