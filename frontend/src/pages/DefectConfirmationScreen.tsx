import React from 'react';
import { ImageReviewScreen } from './ImageReviewScreen';

// Defect confirmation opens as a side panel over the review screen, not a separate narrow page.
export const DefectConfirmationScreen: React.FC = () => {
  return <ImageReviewScreen />;
};
