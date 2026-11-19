import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useSession } from "./lib/session";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LotsPage } from "./pages/LotsPage";
import { NewLotPage } from "./pages/NewLotPage";
import { LotPage } from "./pages/LotPage";
import { PlanPage } from "./pages/PlanPage";
import { CapturePage } from "./pages/CapturePage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { ReviewPage } from "./pages/ReviewPage";
import { DecisionPage } from "./pages/DecisionPage";
import { ReportPage } from "./pages/ReportPage";
import { AuditPage } from "./pages/AuditPage";
import { AdminPage } from "./pages/AdminPage";
import { HowPage } from "./pages/HowPage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { authenticated } = useSession();
  const location = useLocation();
  if (!authenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<RequireAuth><DashboardPage /></RequireAuth>} />
      <Route path="/lots" element={<RequireAuth><LotsPage /></RequireAuth>} />
      <Route path="/lots/new" element={<RequireAuth><NewLotPage /></RequireAuth>} />
      <Route path="/lots/:lotId" element={<RequireAuth><LotPage /></RequireAuth>} />
      <Route path="/lots/:lotId/plan" element={<RequireAuth><PlanPage /></RequireAuth>} />
      <Route path="/lots/:lotId/capture" element={<RequireAuth><CapturePage /></RequireAuth>} />
      <Route path="/lots/:lotId/review" element={<RequireAuth><ReviewQueuePage /></RequireAuth>} />
      <Route path="/review/:imageId" element={<RequireAuth><ReviewPage /></RequireAuth>} />
      <Route path="/lots/:lotId/decision" element={<RequireAuth><DecisionPage /></RequireAuth>} />
      <Route path="/lots/:lotId/report" element={<RequireAuth><ReportPage /></RequireAuth>} />
      <Route path="/audit" element={<RequireAuth><AuditPage /></RequireAuth>} />
      <Route path="/admin" element={<RequireAuth><AdminPage /></RequireAuth>} />
      <Route path="/how" element={<RequireAuth><HowPage /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
