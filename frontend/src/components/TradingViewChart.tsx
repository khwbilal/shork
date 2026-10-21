import { useEffect, useId, useState } from "react";
import { EmptyState } from "./ui";

declare global {
  interface Window {
    TradingView?: {
      widget: new (options: Record<string, unknown>) => unknown;
    };
  }
}

const TV_INTERVAL: Record<string, string> = { "15m": "15", "1h": "60", "4h": "240", "1D": "D" };

let scriptPromise: Promise<void> | null = null;

function loadScript(): Promise<void> {
  if (window.TradingView) return Promise.resolve();
  scriptPromise ??= new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/tv.js";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      scriptPromise = null;
      reject(new Error("Failed to load TradingView widget"));
    };
    document.body.appendChild(script);
  });
  return scriptPromise;
}

export default function TradingViewChart({
  tvSymbol,
  timeframe,
  dark,
}: Readonly<{ tvSymbol: string; timeframe: string; dark: boolean }>) {
  const containerId = `tv_chart_${useId().replace(/:/g, "")}`;
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadScript()
      .then(() => {
        const el = document.getElementById(containerId);
        if (cancelled || !el || !window.TradingView) return;
        setFailed(false);
        el.innerHTML = "";
        new window.TradingView.widget({
          autosize: true,
          symbol: tvSymbol,
          interval: TV_INTERVAL[timeframe] ?? "60",
          timezone: "Etc/UTC",
          theme: dark ? "dark" : "light",
          style: "1",
          locale: "en",
          toolbar_bg: dark ? "#14191D" : "#FFFFFF",
          enable_publishing: false,
          allow_symbol_change: false,
          container_id: containerId,
          studies: ["MAExp@tv-basicstudies"],
        });
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [containerId, tvSymbol, timeframe, dark]);

  if (failed) {
    return (
      <div id="tv_chart">
        <EmptyState text="TradingView chart library did not load. Check your connection." icon="chart" />
      </div>
    );
  }
  // #tv_chart carries the sizing from the shared stylesheet; the inner id is the widget mount.
  return (
    <div id="tv_chart">
      <div id={containerId} style={{ height: "100%" }} />
    </div>
  );
}
