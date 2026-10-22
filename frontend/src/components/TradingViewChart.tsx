import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";
import ShowChart from "@mui/icons-material/ShowChart";
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
  // The widget wants a literal colour; take the paper colour of the active scheme from the theme.
  const theme = useTheme();
  const toolbarBg = theme.colorSchemes[dark ? "dark" : "light"]?.palette.background.paper ?? theme.palette.background.paper;

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
          toolbar_bg: toolbarBg,
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
  }, [containerId, tvSymbol, timeframe, dark, toolbarBg]);

  const size = { height: { xs: 380, md: 520 }, minWidth: 0 };
  if (failed) {
    return (
      <Box id="tv_chart" sx={size}>
        <EmptyState text="TradingView chart library did not load. Check your connection." icon={<ShowChart />} />
      </Box>
    );
  }
  // The outer box sets the size; the inner id is the widget mount.
  return (
    <Box id="tv_chart" sx={size}>
      <div id={containerId} style={{ height: "100%" }} />
    </Box>
  );
}
