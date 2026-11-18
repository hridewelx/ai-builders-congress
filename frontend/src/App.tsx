import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { RoleProvider } from './context/RoleContext';
import { DevToolbar } from './components/DevToolbar';
import { AppLayout } from './components/layout/AppLayout';
import { LoginScreen } from './pages/LoginScreen';
import { DashboardScreen } from './pages/DashboardScreen';
import { LotListScreen } from './pages/LotListScreen';
import { CreateLotScreen } from './pages/CreateLotScreen';
import { LotDetailsScreen } from './pages/LotDetailsScreen';
import { SamplingPlanScreen } from './pages/SamplingPlanScreen';
import { ImageCaptureScreen } from './pages/ImageCaptureScreen';
import { ImageReviewScreen } from './pages/ImageReviewScreen';
import { DefectConfirmationScreen } from './pages/DefectConfirmationScreen';
import { DecisionSummaryScreen } from './pages/DecisionSummaryScreen';
import { ReportViewScreen } from './pages/ReportViewScreen';
import { AdminPanelPage } from './pages/admin/AdminPanelPage';
import { DesignSystemPage } from './pages/DesignSystemPage';

export const App: React.FC = () => {
  return (
    <RoleProvider>
      <BrowserRouter>
        <div className="relative min-h-screen bg-[#F8FAFC]">
          <Routes>
            {/* Screen 1: Login (Standalone full screen) */}
            <Route path="/login" element={<LoginScreen />} />

            {/* Desktop App Layout Shell with Left Sidebar + Top Bar + Fluid 1200px max container */}
            <Route element={<AppLayout />}>
              {/* Screen 2: Dashboard */}
              <Route path="/dashboard" element={<DashboardScreen />} />

              {/* Screen 3: Lot List */}
              <Route path="/lots" element={<LotListScreen />} />

              {/* Screen 4: Create Lot */}
              <Route path="/lots/new" element={<CreateLotScreen />} />

              {/* Screen 5: Lot Details (Control Center) */}
              <Route path="/lots/:id" element={<LotDetailsScreen />} />

              {/* Screen 6: Sampling Plan Configuration */}
              <Route path="/lots/:id/plan" element={<SamplingPlanScreen />} />

              {/* Screen 7: Image Capture */}
              <Route path="/lots/:id/capture" element={<ImageCaptureScreen />} />

              {/* Screen 8: Image Review */}
              <Route path="/lots/:id/review" element={<ImageReviewScreen />} />

              {/* Screen 9: Defect Confirmation */}
              <Route
                path="/lots/:id/defect-confirm/:proposalId"
                element={<DefectConfirmationScreen />}
              />

              {/* Screen 10: Decision Summary & Supervisor Override */}
              <Route path="/lots/:id/decision" element={<DecisionSummaryScreen />} />

              {/* Screen 11: Report View & PDF Download */}
              <Route path="/lots/:id/report" element={<ReportViewScreen />} />

              {/* Desktop Screen 12-17: Admin Panel (6 tabs & URL synchronization) */}
              <Route path="/admin" element={<AdminPanelPage />} />

              {/* Component & Token Showcase (matching 00-design-system.png) */}
              <Route path="/design-system" element={<DesignSystemPage />} />

              {/* Default root path -> Dashboard */}
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
            </Route>

            {/* Fallback route */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>

          {/* Dev-Only Role and Screen Switcher (Floats top-right, compact & out of the way) */}
          <DevToolbar />
        </div>
      </BrowserRouter>
    </RoleProvider>
  );
};

export default App;
