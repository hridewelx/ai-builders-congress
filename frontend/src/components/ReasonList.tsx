import { useSession } from "../lib/session";

export function ReasonList({ codes, showNext = true }: { codes: string[]; showNext?: boolean }) {
  const { reason } = useSession();
  return (
    <div className="reason-grid">
      {codes.map((code) => {
        const entry = reason(code);
        return (
          <div className="reason-row" key={code}>
            <div className="reason-row-head">
              <span className="mono">{code}</span>
              <b>{entry.title}</b>
            </div>
            <p>{entry.text}</p>
            {showNext ? (
              <div className="reason-row-next">
                <span>Next step:</span> {entry.next}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
