import { ShiftView } from "../types";

type HudProps = {
  view: ShiftView;
};

const METERS: Array<{ key: keyof ShiftView["metrics"]; label: string }> = [
  { key: "technical", label: "Technical" },
  { key: "ethical", label: "Ethical" },
  { key: "political", label: "Political" },
  { key: "fatigue", label: "Fatigue" },
];

const formatRemaining = (minutes: number) => `${Math.floor(minutes / 60)}h ${minutes % 60}m`;

const Hud = ({ view }: HudProps) => (
  <section className="card hud" aria-label="Shift status">
    <div className="hud-clock">
      <span className="hud-time">{view.clock_label}</span>
      <span className="hud-remaining">{formatRemaining(view.remaining_minutes)} left</span>
    </div>
    <ul className="meters">
      {METERS.map(({ key, label }) => (
        <li key={key} className="meter">
          <span className="meter-label">{label}</span>
          <div
            className={`meter-bar meter-${key}`}
            role="meter"
            aria-label={label}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={view.metrics[key]}
          >
            <div className="meter-fill" style={{ width: `${view.metrics[key]}%` }} />
          </div>
          <span className="meter-value">{view.metrics[key]}</span>
        </li>
      ))}
    </ul>
  </section>
);

export default Hud;
