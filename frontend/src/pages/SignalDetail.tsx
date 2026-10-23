import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import ArrowBack from "@mui/icons-material/ArrowBack";
import ExpandMore from "@mui/icons-material/ExpandMore";
import Refresh from "@mui/icons-material/Refresh";
import { useCallback, useEffect, useState } from "react";
import { api, type Signal, type StrategyPackResult } from "../api";
import { useFeedback } from "../components/feedback";
import { ActionButton, EmptyState, Na, PageHeader, SectionCard, V } from "../components/ui";
import { GLYPH, biasClass, fmtPx, fmtSigned, humanize, isNum } from "../lib/format";

const OPT_LABEL: Record<string, string> = {
  local_score: "Local score",
  ai_ensemble: "Full AI ensemble",
  majority_vote: "Majority vote",
};

function stanceLabel(s: string | null | undefined): string {
  if (s === "hold") return "Hold";
  if (s === "caution") return "Caution";
  if (s === "exit_early") return "Exit early";
  return "—";
}

export default function SignalDetail({
  signalId,
  onBack,
  onReviewed,
}: Readonly<{
  signalId: string;
  onBack: () => void;
  onReviewed?: () => void;
}>) {
  const { toast } = useFeedback();
  const [sig, setSig] = useState<Signal | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const res = await api.getSignal(signalId);
      setSig(res.signal);
    } catch (e) {
      setSig(null);
      setErr((e as Error).message);
    }
  }, [signalId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function runReview() {
    if (!sig || busy) return;
    setBusy(true);
    try {
      const res = await api.reviewSignal(sig.id);
      setSig(res.signal);
      toast(res.review?.summary ?? "Review saved");
      onReviewed?.();
    } catch (e) {
      toast(`Review failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  if (err) {
    return (
      <Stack spacing={2}>
        <PageHeader
          title="Signal"
          subtitle={err}
          actions={
            <ActionButton icon={<ArrowBack />} onClick={onBack}>
              Back to Signals
            </ActionButton>
          }
        />
        <EmptyState text={err} />
      </Stack>
    );
  }

  if (!sig) {
    return (
      <Stack spacing={2}>
        <PageHeader title="Signal" subtitle="Loading…" />
        <EmptyState text="Loading signal…" />
      </Stack>
    );
  }

  const multi = sig.multi_analysis_json;
  const packs: StrategyPackResult[] = multi?.packs ?? [];
  const reviews = sig.live_review_json ?? [];
  const cls = biasClass(sig.bias);
  const optMode = multi?.optimize_mode ? OPT_LABEL[multi.optimize_mode] ?? multi.optimize_mode : null;

  return (
    <Stack spacing={2}>
      <PageHeader
        title={`${sig.symbol} · ${sig.bias}`}
        subtitle={`${humanize(sig.strategy_id ?? "desk")} · ${sig.timeframe ?? "—"} · ${sig.status}${
          optMode ? ` · ${optMode}` : ""
        }`}
        actions={
          <>
            <ActionButton icon={<ArrowBack />} onClick={onBack}>
              Back
            </ActionButton>
            {sig.status === "open" ? (
              <ActionButton icon={<Refresh />} primary busy={busy} busyLabel="Reviewing…" onClick={() => void runReview()}>
                Live review
              </ActionButton>
            ) : null}
          </>
        }
      />

      <SectionCard title="Original plan (frozen)">
        <Box
          sx={{
            display: "grid",
            gap: 1.5,
            gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(4, 1fr)" },
          }}
        >
          <Box>
            <Typography variant="caption" color="text.secondary">
              Bias
            </Typography>
            <Typography className={cls}>
              {GLYPH[cls]} {sig.bias}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Entry
            </Typography>
            <Typography>
              <V value={fmtPx(sig.entry)} />
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Stop
            </Typography>
            <Typography>
              <V value={fmtPx(sig.stop_loss)} />
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Target
            </Typography>
            <Typography>
              <V value={fmtPx(sig.take_profit)} />
            </Typography>
          </Box>
        </Box>
        {sig.notes ? (
          <Typography variant="body2" sx={{ mt: 1.5, color: "text.secondary" }}>
            {sig.notes}
          </Typography>
        ) : null}
        {multi?.reason ? (
          <Typography variant="body2" sx={{ mt: 1 }}>
            Optimize: {multi.reason}
          </Typography>
        ) : null}
      </SectionCard>

      {packs.length > 0 ? (
        <SectionCard title={`Strategy packs (${String(packs.length)})`}>
          {packs.map((p) => {
            const pCls = biasClass(p.bias);
            const winner = multi?.final_strategy_id === p.strategy_id;
            return (
              <Accordion key={p.strategy_id} disableGutters elevation={0} sx={{ "&:before": { display: "none" } }}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap" }}>
                    <Typography sx={{ fontWeight: winner ? 700 : 500 }}>{p.strategy_label || p.strategy_id}</Typography>
                    {winner ? <Chip size="small" label="Winner" color="primary" /> : null}
                    <Chip size="small" label={`${GLYPH[pCls]} ${p.bias}`} variant="outlined" />
                    <Typography variant="caption" color="text.secondary">
                      score {isNum(p.pack_score) ? String(p.pack_score) : "—"} · fit{" "}
                      {fmtSigned(p.fit_score) ?? "—"} · {p.timeframe ?? "—"}
                    </Typography>
                  </Stack>
                </AccordionSummary>
                <AccordionDetails>
                  <Typography variant="body2">
                    Entry <V value={fmtPx(p.entry)} /> · SL <V value={fmtPx(p.stop_loss)} /> · TP{" "}
                    <V value={fmtPx(p.take_profit)} />
                  </Typography>
                  {p.reasoning ? (
                    <Typography variant="body2" sx={{ mt: 1, color: "text.secondary" }}>
                      {p.reasoning}
                    </Typography>
                  ) : null}
                  {p.error ? (
                    <Typography variant="body2" color="error" sx={{ mt: 1 }}>
                      {p.error}
                    </Typography>
                  ) : null}
                </AccordionDetails>
              </Accordion>
            );
          })}
        </SectionCard>
      ) : (
        <SectionCard title="Strategy packs">
          <Typography variant="body2" color="text.secondary">
            Single-strategy signal (no multi pack snapshot).
          </Typography>
        </SectionCard>
      )}

      <SectionCard title={`Live reviews (${String(reviews.length)})`}>
        {reviews.length === 0 ? (
          <EmptyState text="No live reviews yet. Use Live review to append stance and optional revised levels." />
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>When</TableCell>
                <TableCell>Price</TableCell>
                <TableCell>R</TableCell>
                <TableCell>Stance</TableCell>
                <TableCell>Revised SL / TP</TableCell>
                <TableCell>Note</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {[...reviews].reverse().map((r) => (
                <TableRow key={r.at}>
                  <TableCell>{r.at?.slice(0, 19)?.replace("T", " ") ?? <Na />}</TableCell>
                  <TableCell>
                    <V value={fmtPx(r.price)} />
                  </TableCell>
                  <TableCell>{isNum(r.unrealized_r) ? `${r.unrealized_r > 0 ? "+" : ""}${r.unrealized_r}` : <Na />}</TableCell>
                  <TableCell>{stanceLabel(r.stance)}</TableCell>
                  <TableCell>
                    {r.levels_changed ? (
                      <>
                        <V value={fmtPx(r.revised_stop_loss)} /> / <V value={fmtPx(r.revised_take_profit)} />
                      </>
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        unchanged
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">{r.summary}</Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>
    </Stack>
  );
}
