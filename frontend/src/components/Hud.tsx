import { ShiftView } from "../types";

type HudProps = {
  view: ShiftView;
};

const METERS: Array<{ key: keyof ShiftView["metrics"]; label: string; hint?: string }> = [
  { key: "technical", label: "Technical" },
  { key: "ethical", label: "Ethical" },
  { key: "political", label: "Political" },
  { key: "fatigue", label: "Fatigue", hint: "higher is worse" },
];

const formatRemaining = (minutes: number) => `${Math.floor(minutes / 60)}h ${minutes % 60}m`;

const Hud = ({ view }: HudProps) => (
  <section className="card hud" aria-label="Shift status">
    <div className="hud-clock">
      <span className="hud-time">{view.clock_label}</span>
      <span className="hud-remaining">{formatRemaining(view.remaining_minutes)} left</span>
    </div>
    <ul className="meters">
      {METERS.map(({ key, label, hint }) => {
        const value = view.metrics[key];
        return (
          <li key={key} className="meter">
            <span className="meter-label" id={`meter-${key}`} aria-hidden="true">
              {label}
            </span>
            <div
              className={`meter-bar meter-${key}`}
              role="meter"
              aria-labelledby={`meter-${key}`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={value}
              aria-valuetext={hint ? `${value} of 100, ${hint}` : `${value} of 100`}
            >
              <div className="meter-fill" style={{ width: `${value}%` }} />
            </div>
            <span className="meter-value" aria-hidden="true">
              {value}
            </span>
          </li>
        );
      })}
    </ul>
  </section>
);

export default Hud;
