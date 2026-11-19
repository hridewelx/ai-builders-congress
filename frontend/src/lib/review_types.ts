/* Shapes returned by /api/lots/{id}/review, shared by page and cards. */
export interface Prediction {
  id: number;
  defect_type: string;
  confirmed_type: string | null;
  score: number;
  x1: number; y1: number; x2: number; y2: number;
  review_state: string;
  provisional_critical: number;
  severity: string | null;
  zone_code: string | null;
  size_band: string | null;
  clause_ref: string | null;
  second_review: string | null;
  note: string | null;
  reviewer: string | null;
  reviewed_by: number | null;
}

export interface ReviewData {
  lot: { id: number; lot_code: string; buyer_name: string; status: string };
  image: { id: number; sha256_working: string; width: number; height: number; bytes: number };
  view: { garment_code: string; side: string };
  review: { state: string; note: string | null; reviewer: string | null } | null;
  job: { status: string; model_version: string; error?: string } | null;
  preds: Prediction[];
  status: string;
  next_item: { view: { image: { id: number } } } | null;
  can_write: boolean;
  is_supervisor: boolean;
  user: { id: number };
  zones: string[];
  human_classes: string[];
}
