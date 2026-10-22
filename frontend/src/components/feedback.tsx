import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import SnackbarContent from "@mui/material/SnackbarContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

/** Toasts and the one shared confirm and input dialog; never window.confirm or prompt (ruleset 9.3). */

export type AskOptions = {
  title: string;
  text?: string;
  label?: string;
  okLabel?: string;
  danger?: boolean;
  input?: boolean;
};

type Feedback = {
  toast: (text: string) => void;
  /** Resolves to the input text (or true without input), or null when cancelled. */
  ask: (opts: AskOptions) => Promise<string | true | null>;
};

const FeedbackContext = createContext<Feedback | null>(null);

export function useFeedback(): Feedback {
  const ctx = useContext(FeedbackContext);
  if (!ctx) throw new Error("useFeedback must be used inside <FeedbackProvider>");
  return ctx;
}

type Toast = { id: number; text: string };
type Pending = AskOptions & { resolve: (v: string | true | null) => void };

export function FeedbackProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [pending, setPending] = useState<Pending | null>(null);
  const nextId = useRef(0);

  const toast = useCallback((text: string) => {
    nextId.current += 1;
    const id = nextId.current;
    setToasts((t) => [...t, { id, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3800);
  }, []);

  const ask = useCallback(
    (opts: AskOptions) => new Promise<string | true | null>((resolve) => setPending({ ...opts, resolve })),
    [],
  );

  const value = useMemo(() => ({ toast, ask }), [toast, ask]);

  return (
    <FeedbackContext.Provider value={value}>
      {children}
      {pending ? (
        <AskDialog
          opts={pending}
          onDone={(v) => {
            pending.resolve(v);
            setPending(null);
          }}
        />
      ) : null}
      <Stack
        spacing={1}
        aria-live="polite"
        sx={{
          position: "fixed",
          zIndex: (t) => t.zIndex.snackbar,
          bottom: 16,
          left: { xs: 16, sm: "auto" },
          right: 16,
          maxWidth: { sm: 420 },
          pointerEvents: "none",
        }}
      >
        {toasts.map((t) => (
          <SnackbarContent key={t.id} message={t.text} sx={{ pointerEvents: "auto" }} />
        ))}
      </Stack>
    </FeedbackContext.Provider>
  );
}

function AskDialog({ opts, onDone }: Readonly<{ opts: AskOptions; onDone: (v: string | true | null) => void }>) {
  const [text, setText] = useState("");
  return (
    <Dialog
      open
      onClose={() => onDone(null)}
      fullWidth
      maxWidth="xs"
      aria-labelledby="askTitle"
      slotProps={{
        paper: {
          component: "form",
          onSubmit: (e: React.FormEvent) => {
            e.preventDefault();
            onDone(opts.input ? text.trim() : true);
          },
        },
      }}
    >
      <DialogTitle id="askTitle">{opts.title}</DialogTitle>
      <DialogContent>
        {opts.text ? <DialogContentText sx={{ mb: opts.input ? 2 : 0 }}>{opts.text}</DialogContentText> : null}
        {opts.input ? (
          <TextField
            autoFocus
            fullWidth
            label={opts.label}
            value={text}
            onChange={(e) => setText(e.target.value)}
            slotProps={{ htmlInput: { inputMode: "decimal", autoComplete: "off" } }}
          />
        ) : null}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button color="inherit" onClick={() => onDone(null)}>
          Cancel
        </Button>
        <Button type="submit" variant="contained" color={opts.danger ? "error" : "primary"} autoFocus={!opts.input}>
          {opts.okLabel ?? "Confirm"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
