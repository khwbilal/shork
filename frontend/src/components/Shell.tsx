import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import ListSubheader from "@mui/material/ListSubheader";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Toolbar from "@mui/material/Toolbar";
import AppBar from "@mui/material/AppBar";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useColorScheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";
import CalendarMonthOutlined from "@mui/icons-material/CalendarMonthOutlined";
import CandlestickChartOutlined from "@mui/icons-material/CandlestickChartOutlined";
import Check from "@mui/icons-material/Check";
import ChevronLeft from "@mui/icons-material/ChevronLeft";
import ChevronRight from "@mui/icons-material/ChevronRight";
import DarkModeOutlined from "@mui/icons-material/DarkModeOutlined";
import FormatListBulleted from "@mui/icons-material/FormatListBulleted";
import LightModeOutlined from "@mui/icons-material/LightModeOutlined";
import MenuBookOutlined from "@mui/icons-material/MenuBookOutlined";
import MenuIcon from "@mui/icons-material/Menu";
import Search from "@mui/icons-material/Search";
import SettingsBrightnessOutlined from "@mui/icons-material/SettingsBrightnessOutlined";
import ShowChart from "@mui/icons-material/ShowChart";
import TrackChanges from "@mui/icons-material/TrackChanges";
import { useEffect, useRef, useState, type ReactElement } from "react";
import type { HealthResponse } from "../api";
import { EXCHANGES, PAGES, PROVIDER_LABEL, TIMEFRAMES, type PageKey } from "../lib/nav";
import { RAIL_FOLDED, RAIL_WIDTH, TOPBAR_HEIGHT } from "../theme";
import JobsStatus from "./JobsStatus";
import PairSearch from "./PairSearch";
import { monoSx } from "./ui";

const NAV_ICON: Record<PageKey, ReactElement> = {
  desk: <CandlestickChartOutlined />,
  watchlist: <FormatListBulleted />,
  calendar: <CalendarMonthOutlined />,
  journal: <MenuBookOutlined />,
  signals: <TrackChanges />,
};

function NavItem({
  page,
  current,
  count,
  folded,
}: Readonly<{ page: PageKey; current: PageKey; count?: number; folded: boolean }>) {
  const selected = current === page;
  const item = (
    <ListItemButton
      component="a"
      href={`#/${page}`}
      selected={selected}
      aria-current={selected ? "page" : undefined}
      sx={{
        mx: 1,
        my: 0.25,
        borderRadius: 1,
        minHeight: 40,
        px: folded ? 0 : 1.5,
        justifyContent: folded ? "center" : "flex-start",
        "&.Mui-selected": { color: "primary.main", bgcolor: "surface.action" },
        "&.Mui-selected .MuiListItemIcon-root": { color: "primary.main" },
      }}
    >
      <ListItemIcon sx={{ minWidth: 0, mr: folded ? 0 : 1.5, "& svg": { fontSize: 20 } }}>{NAV_ICON[page]}</ListItemIcon>
      {folded ? null : (
        <>
          <ListItemText primary={PAGES[page]} slotProps={{ primary: { variant: "body2", sx: { fontWeight: 600 } } }} />
          {count ? <Chip size="small" label={count} sx={[monoSx, { height: 20 }]} /> : null}
        </>
      )}
    </ListItemButton>
  );
  return folded ? (
    <Tooltip title={count ? `${PAGES[page]} · ${String(count)} open` : PAGES[page]} placement="right">
      {item}
    </Tooltip>
  ) : (
    item
  );
}

function ProviderChip({
  health,
  healthError,
  folded,
}: Readonly<{ health: HealthResponse | null; healthError: boolean; folded: boolean }>) {
  const on = Boolean(health && health.ai_provider !== "none");
  let name = "Checking…";
  let detail = "";
  if (healthError) {
    name = "Backend offline";
    detail = "Start the API on :8000";
  } else if (health) {
    name = PROVIDER_LABEL[health.ai_provider] ?? health.ai_provider;
    detail = on ? (health.ai_model ?? "") : "Pick one in start.ps1 / start.sh";
  }
  let dot = "text.disabled";
  if (healthError || (health && !on)) dot = "warning.main";
  else if (on) dot = "primary.main";
  const title = `AI: ${name}${health?.ai_model ? ` (${health.ai_model})` : ""}`;
  return (
    <Tooltip title={title} placement="right">
      <Stack
        direction="row"
        spacing={1}
       
        sx={{ alignItems: "center",
          px: folded ? 0 : 1.5,
          py: 1,
          justifyContent: folded ? "center" : "flex-start",
          border: 1,
          borderColor: "divider",
          borderRadius: 1,
          bgcolor: "surface.paper2",
          minHeight: 44,
        }}
      >
        <Box component="span" aria-hidden sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: dot, flexShrink: 0 }} />
        {folded ? null : (
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="caption" component="div" noWrap sx={{ fontWeight: 700, lineHeight: 1.3 }}>
              {name}
            </Typography>
            <Typography variant="caption" component="div" noWrap sx={{ color: "text.secondary", lineHeight: 1.3 }}>
              {detail || <span aria-hidden>&nbsp;</span>}
            </Typography>
          </Box>
        )}
      </Stack>
    </Tooltip>
  );
}

function RailContent({
  page,
  health,
  healthError,
  journalOpen,
  signalsOpen,
  folded,
  onToggleFold,
}: Readonly<{
  page: PageKey;
  health: HealthResponse | null;
  healthError: boolean;
  journalOpen: number;
  signalsOpen: number;
  folded: boolean;
  onToggleFold?: () => void;
}>) {
  return (
    <Stack sx={{ height: "100%", overflowX: "hidden" }} component="nav" aria-label="Main navigation">
      <Stack direction="row" spacing={1.25} sx={{ alignItems: "center", height: TOPBAR_HEIGHT, px: folded ? 0 : 2, justifyContent: folded ? "center" : "flex-start", flexShrink: 0 }}>
        <Box
          sx={{
            width: 32,
            height: 32,
            borderRadius: 1,
            bgcolor: "brand",
            color: "common.white",
            display: "grid",
            placeItems: "center",
            flexShrink: 0,
          }}
        >
          <ShowChart fontSize="small" />
        </Box>
        {folded ? null : (
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="body2" component="div" sx={{ fontWeight: 700, lineHeight: 1.2 }} noWrap>
              Chart AI
            </Typography>
            <Typography variant="caption" component="div" sx={{ color: "text.secondary", lineHeight: 1.2 }} noWrap>
              Crypto analysis desk
            </Typography>
          </Box>
        )}
      </Stack>
      <List dense sx={{ flex: 1, overflowY: "auto", pt: 1 }}>
        <NavItem page="desk" current={page} folded={folded} />
        <NavItem page="watchlist" current={page} folded={folded} />
        <NavItem page="calendar" current={page} folded={folded} />
        {folded ? (
          <Box sx={{ mx: 2, my: 1, borderTop: 1, borderColor: "divider" }} />
        ) : (
          <ListSubheader disableSticky sx={{ bgcolor: "transparent", lineHeight: "32px", fontSize: "0.6875rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Track record
          </ListSubheader>
        )}
        <NavItem page="journal" current={page} count={journalOpen} folded={folded} />
        <NavItem page="signals" current={page} count={signalsOpen} folded={folded} />
      </List>
      <Stack spacing={1} sx={{ p: 1, borderTop: 1, borderColor: "divider", flexShrink: 0 }}>
        <JobsStatus folded={folded} />
        <ProviderChip health={health} healthError={healthError} folded={folded} />
        {onToggleFold ? (
          <Box sx={{ display: "flex", justifyContent: folded ? "center" : "flex-end" }}>
            <IconButton size="small" aria-label={folded ? "Expand navigation" : "Collapse navigation"} onClick={onToggleFold}>
              {folded ? <ChevronRight fontSize="small" /> : <ChevronLeft fontSize="small" />}
            </IconButton>
          </Box>
        ) : null}
      </Stack>
    </Stack>
  );
}

export function Rail({
  desktop,
  mobileOpen,
  onCloseMobile,
  folded,
  onToggleFold,
  ...rest
}: Readonly<{
  desktop: boolean;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  page: PageKey;
  health: HealthResponse | null;
  healthError: boolean;
  journalOpen: number;
  signalsOpen: number;
  folded: boolean;
  onToggleFold: () => void;
}>) {
  if (!desktop) {
    return (
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onCloseMobile}
        ModalProps={{ keepMounted: true }}
        slotProps={{ paper: { sx: { width: RAIL_WIDTH, bgcolor: "background.paper" } } }}
      >
        <RailContent {...rest} folded={false} />
      </Drawer>
    );
  }
  const width = folded ? RAIL_FOLDED : RAIL_WIDTH;
  return (
    <Drawer
      variant="permanent"
      sx={{
        width,
        flexShrink: 0,
        transition: (t) => t.transitions.create("width", { duration: t.transitions.duration.shorter }),
      }}
      slotProps={{
        paper: {
          sx: {
            width,
            overflowX: "hidden",
            transition: (t) => t.transitions.create("width", { duration: t.transitions.duration.shorter }),
          },
        },
      }}
    >
      <RailContent {...rest} folded={folded} onToggleFold={onToggleFold} />
    </Drawer>
  );
}

type Mode = "system" | "light" | "dark";
const MODE_LABEL: Record<Mode, string> = { system: "System", light: "Light", dark: "Dark" };
const MODE_ICON: Record<Mode, ReactElement> = {
  system: <SettingsBrightnessOutlined fontSize="small" />,
  light: <LightModeOutlined fontSize="small" />,
  dark: <DarkModeOutlined fontSize="small" />,
};

/** System, light or dark; MUI keeps the choice in localStorage (cca_theme). */
function ThemeToggle() {
  const { mode, setMode } = useColorScheme();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const current: Mode = mode ?? "system";
  return (
    <>
      <Tooltip title={`Theme: ${MODE_LABEL[current]}`}>
        <IconButton aria-label={`Theme: ${MODE_LABEL[current]}. Change theme`} onClick={(e) => setAnchor(e.currentTarget)}>
          {MODE_ICON[current]}
        </IconButton>
      </Tooltip>
      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
        {(Object.keys(MODE_LABEL) as Mode[]).map((m) => (
          <MenuItem
            key={m}
            selected={m === current}
            onClick={() => {
              setMode(m);
              setAnchor(null);
            }}
          >
            <ListItemIcon>{MODE_ICON[m]}</ListItemIcon>
            <ListItemText>{MODE_LABEL[m]}</ListItemText>
            {m === current ? <Check fontSize="small" sx={{ ml: 2 }} /> : null}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}

function TimeframeToggle({ timeframe, onTimeframe }: Readonly<{ timeframe: string; onTimeframe: (tf: string) => void }>) {
  return (
    <ToggleButtonGroup
      exclusive
      size="small"
      color="primary"
      value={timeframe}
      aria-label="Timeframe"
      onChange={(_e, v: string | null) => {
        if (v) onTimeframe(v);
      }}
      sx={{ flexShrink: 0 }}
    >
      {TIMEFRAMES.map((tf) => (
        <ToggleButton key={tf} value={tf} sx={[monoSx, { px: 1.25, fontSize: "0.75rem" }]}>
          {tf}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
}

export function TopBar({
  page,
  symbol,
  exchange,
  timeframe,
  desktop,
  onMenu,
  onExchange,
  onTimeframe,
  onPickPair,
  onPickPage,
}: Readonly<{
  page: PageKey;
  symbol: string;
  exchange: string;
  timeframe: string;
  desktop: boolean;
  onMenu: () => void;
  onExchange: (ex: string) => void;
  onTimeframe: (tf: string) => void;
  onPickPair: (symbol: string, exchange?: string, tv?: string) => void;
  onPickPage: (page: PageKey) => void;
}>) {
  const inline = useMediaQuery((t) => t.breakpoints.up("md"));
  const phone = useMediaQuery((t) => t.breakpoints.down("sm"));
  const [dialogOpen, setDialogOpen] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  // Ctrl K / Cmd K focuses the search (or opens it on smaller screens).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (inline && searchRef.current) searchRef.current.focus();
        else setDialogOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [inline]);

  const openSearch = () => {
    if (inline && searchRef.current) searchRef.current.focus();
    else setDialogOpen(true);
  };

  const pairButton = (
    <Tooltip title="Change pair (Ctrl K)">
      <Box
        component="button"
        type="button"
        onClick={openSearch}
        sx={[
          monoSx,
          {
            all: "unset",
            cursor: "pointer",
            fontWeight: 700,
            fontSize: "0.875rem",
            px: 1,
            minHeight: { xs: 48, sm: 36 },
            display: "inline-flex",
            alignItems: "center",
            borderRadius: 1,
            minWidth: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            "&:hover": { bgcolor: "action.hover" },
            "&:focus-visible": { outline: 2, outlineColor: "primary.main" },
          },
        ]}
      >
        {symbol}
      </Box>
    </Tooltip>
  );

  const exchangeSelect = (
    <Select
      size="small"
      value={exchange}
      onChange={(e) => onExchange(e.target.value)}
      inputProps={{ "aria-label": "Exchange" }}
      sx={{ fontSize: "0.8125rem", flexShrink: 0, "& .MuiSelect-select": { py: 0.75 } }}
    >
      {EXCHANGES.map((ex) => (
        <MenuItem key={ex} value={ex}>
          {ex}
        </MenuItem>
      ))}
    </Select>
  );

  return (
    <AppBar
      position="sticky"
      color="inherit"
      elevation={0}
      sx={{ bgcolor: "background.paper", borderBottom: 1, borderColor: "divider", zIndex: (t) => t.zIndex.appBar }}
    >
      <Toolbar disableGutters sx={{ minHeight: `${String(TOPBAR_HEIGHT)}px !important`, px: { xs: 1, sm: 2 }, gap: 1 }}>
        {desktop ? null : (
          <IconButton aria-label="Open navigation" onClick={onMenu} edge="start">
            <MenuIcon />
          </IconButton>
        )}
        <Typography variant="h1" component="h1" noWrap sx={{ display: { xs: phone ? "block" : "none", lg: "block" }, mr: 1, flexShrink: 0 }}>
          {PAGES[page]}
        </Typography>
        {phone ? null : (
          <Stack direction="row" spacing={1} sx={{ alignItems: "center", minWidth: 0 }}>
            {pairButton}
            {exchangeSelect}
            <TimeframeToggle timeframe={timeframe} onTimeframe={onTimeframe} />
          </Stack>
        )}
        <Box sx={{ flex: 1 }} />
        {inline ? (
          <Box sx={{ width: { md: 240, lg: 320 }, flexShrink: 1, minWidth: 160 }}>
            <PairSearch ref={searchRef} exchange={exchange} onPickPair={onPickPair} onPickPage={onPickPage} />
          </Box>
        ) : (
          <Tooltip title="Search pairs">
            <IconButton aria-label="Search pairs" onClick={() => setDialogOpen(true)}>
              <Search />
            </IconButton>
          </Tooltip>
        )}
        <ThemeToggle />
      </Toolbar>
      {phone ? (
        <Toolbar disableGutters variant="dense" sx={{ px: 1, gap: 1, borderTop: 1, borderColor: "divider", minHeight: 52 }}>
          <Box sx={{ flex: 1, minWidth: 0, display: "flex" }}>{pairButton}</Box>
          <TimeframeToggle timeframe={timeframe} onTimeframe={onTimeframe} />
        </Toolbar>
      ) : null}
      <Dialog
        open={dialogOpen && !inline}
        onClose={() => setDialogOpen(false)}
        fullScreen={phone}
        fullWidth
        maxWidth="sm"
        aria-label="Search pairs"
        slotProps={{ paper: { sx: { alignSelf: phone ? "stretch" : "flex-start", mt: phone ? 0 : 8 } } }}
      >
        <DialogContent sx={{ p: 2 }}>
          <PairSearch
            exchange={exchange}
            autoFocus
            onPickPair={onPickPair}
            onPickPage={onPickPage}
            onDone={() => setDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </AppBar>
  );
}
