import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

/** Toasts and the confirm/input dialog — never window.confirm / prompt. */

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
  /** Resolves to the input text (or "" / true without input), or null when cancelled. */
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
      <div className="toasts" aria-live="polite">
        {toasts.map((t) => (
          <div className="toast" key={t.id}>
            {t.text}
          </div>
        ))}
      </div>
    </FeedbackContext.Provider>
  );
}

function AskDialog({ opts, onDone }: Readonly<{ opts: AskOptions; onDone: (v: string | true | null) => void }>) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const okRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    (opts.input ? inputRef.current : okRef.current)?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onDone(null);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [opts.input, onDone]);

  return (
    <div className="overlay">
      <form
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialogTitle"
        onSubmit={(e) => {
          e.preventDefault();
          onDone(opts.input ? text.trim() : true);
        }}
      >
        <h3 id="dialogTitle">{opts.title}</h3>
        <p>{opts.text ?? ""}</p>
        {opts.input ? (
          <div className="field">
            <label htmlFor="dialogInput">{opts.label}</label>
            <input
              id="dialogInput"
              ref={inputRef}
              inputMode="decimal"
              autoComplete="off"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </div>
        ) : null}
        <div className="actions">
          <button className="btn" type="button" onClick={() => onDone(null)}>
            Cancel
          </button>
          <button className={`btn ${opts.danger ? "danger" : "primary"}`} type="submit" ref={okRef}>
            {opts.okLabel ?? "Confirm"}
          </button>
        </div>
      </form>
    </div>
  );
}
