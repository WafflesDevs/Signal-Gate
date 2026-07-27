import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { Link, Navigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useAuth } from "../auth/AuthContext";
import { useApi } from "../lib/api";
import { UserMenu } from "../components/layout/UserMenu";
import { ChartSidebar } from "../components/charts/ChartSidebar";
import { API_BASE, detectPriceTicker } from "../lib/charts";

type TradeRequest = {
  name: string;
  arguments: Record<string, unknown>;
};

/** Exits the user typed on the Approve card (optional). */
type ExitPlan = {
  ticker: string;
  stop_loss?: number;
  take_profit?: number;
  qty?: number;
};

const BUY_TRADE_NAMES = new Set(["execute_trade", "buy_max_trade"]);

function isBuyTrade(t: TradeRequest) {
  return BUY_TRADE_NAMES.has(t.name);
}

function tradeTicker(t: TradeRequest): string {
  return String(t.arguments?.ticker || "").trim().toUpperCase();
}

function tradeQty(t: TradeRequest): number | null {
  const raw = t.arguments?.qty;
  const n = typeof raw === "number" ? raw : Number(raw);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function formatUsd(n: number) {
  const abs = Math.abs(n);
  const formatted =
    abs >= 1000
      ? abs.toLocaleString(undefined, { maximumFractionDigits: 2 })
      : abs.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
  return `${n < 0 ? "-" : "+"}$${formatted}`;
}

/** Spot price for Live: $… on the Approve card (same rules as Charts). */
function formatLivePrice(n: number) {
  if (n >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  if (n >= 1) return n.toLocaleString(undefined, { maximumFractionDigits: 4 });
  return n.toFixed(6);
}

function parseExitPrice(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  return Number.isFinite(n) && n > 0 ? n : null;
}

type PriceFlash = "up" | "down" | "";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata?: {
    pending_trades?: TradeRequest[];
    resolved?: boolean;
    resolution?: "approve" | "reject" | string;
    chart_ticker?: string;
  };
};

type Conversation = {
  id: string;
  title: string;
  updated_at?: string;
};

const suggestions = [
  "What’s my portfolio worth?",
  "Buy 0.01 BTC",
  "Price of ETH right now",
  "Sell all SOL",
];

/** Match backend caps in app/routers/chat.py */
const MAX_CHATS = 5;
const MAX_MESSAGES = 30;

const CHAT_LIMIT_MSG =
  "Chat limit reached (5). Delete a chat in the sidebar to open a new one.";
const MESSAGE_LIMIT_MSG =
  "Message limit reached (30). Delete this chat and open a new one.";

function tradeLabel(t: TradeRequest) {
  const args = t.arguments || {};
  const qty = args.qty ?? "?";
  const ticker = args.ticker ?? "";
  return `${t.name} · ${qty} ${ticker}`.trim();
}

/**
 * Stop-loss / take-profit inputs for a pending buy.
 * Empty = no exit. Invalid numbers block Approve via onValidityChange.
 * `livePrice` is the polled spot used as entry for SL/TP checks + P/L.
 */
function TradeExitFields({
  trade,
  disabled,
  livePrice,
  priceError,
  onValidityChange,
  onPlanChange,
}: {
  trade: TradeRequest;
  disabled: boolean;
  livePrice: number | null;
  priceError?: string;
  onValidityChange: (ok: boolean) => void;
  onPlanChange: (plan: ExitPlan | null) => void;
}) {
  const ticker = tradeTicker(trade);
  const qty = tradeQty(trade);
  const entry = livePrice;
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");

  const slParsed = parseExitPrice(stopLoss);
  const tpParsed = parseExitPrice(takeProfit);
  const slFilled = stopLoss.trim() !== "";
  const tpFilled = takeProfit.trim() !== "";

  let slError = "";
  let tpError = "";
  if (slFilled && slParsed == null) slError = "Enter a valid stop-loss price";
  else if (slParsed != null && entry != null && slParsed >= entry) {
    slError = "Stop loss must be below entry";
  }
  if (tpFilled && tpParsed == null) tpError = "Enter a valid take-profit price";
  else if (tpParsed != null && entry != null && tpParsed <= entry) {
    tpError = "Take profit must be above entry";
  }
  if (
    !slError &&
    !tpError &&
    slParsed != null &&
    tpParsed != null &&
    slParsed >= tpParsed
  ) {
    slError = "Stop loss must be below take profit";
  }

  const fieldsOk = !slError && !tpError;
  // Empty exits are fine even if price hasn't loaded yet
  const hasAnyExit = slFilled || tpFilled;
  const valid = fieldsOk && (!hasAnyExit || entry != null);

  useEffect(() => {
    onValidityChange(valid);
  }, [valid, onValidityChange]);

  useEffect(() => {
    if (!valid || !ticker || !hasAnyExit) {
      onPlanChange(null);
      return;
    }
    const plan: ExitPlan = { ticker };
    if (slParsed != null) plan.stop_loss = slParsed;
    if (tpParsed != null) plan.take_profit = tpParsed;
    if (qty != null) plan.qty = qty;
    onPlanChange(plan);
  }, [
    valid,
    ticker,
    hasAnyExit,
    slParsed,
    tpParsed,
    qty,
    onPlanChange,
  ]);

  const slPl =
    entry != null && slParsed != null
      ? (slParsed - entry) * (qty ?? 1)
      : null;
  const tpPl =
    entry != null && tpParsed != null
      ? (tpParsed - entry) * (qty ?? 1)
      : null;

  return (
    <div className="trade-card__exits">
      <div className="trade-card__exits-hint">
        Stop loss / take profit (USD)
        {entry != null && (
          <span className="trade-card__entry">
            {" "}
            · entry ≈ ${formatLivePrice(entry)}
          </span>
        )}
      </div>
      {priceError && !entry && (
        <p className="trade-card__exit-error">{priceError}</p>
      )}

      <label className="trade-card__exit-field">
        <span>Stop loss</span>
        <input
          type="number"
          inputMode="decimal"
          min={0}
          step="any"
          placeholder="e.g. 90000"
          value={stopLoss}
          disabled={disabled}
          onChange={(e) => setStopLoss(e.target.value)}
        />
        {slError && <span className="trade-card__exit-error">{slError}</span>}
        {!slError && slPl != null && (
          <span className="trade-card__pl trade-card__pl--loss">
            Est. loss: {formatUsd(slPl)}
            {qty == null ? " / coin" : ""}
          </span>
        )}
      </label>

      <label className="trade-card__exit-field">
        <span>Take profit</span>
        <input
          type="number"
          inputMode="decimal"
          min={0}
          step="any"
          placeholder="e.g. 110000"
          value={takeProfit}
          disabled={disabled}
          onChange={(e) => setTakeProfit(e.target.value)}
        />
        {tpError && <span className="trade-card__exit-error">{tpError}</span>}
        {!tpError && tpPl != null && (
          <span className="trade-card__pl trade-card__pl--profit">
            Est. profit: {formatUsd(tpPl)}
            {qty == null ? " / coin" : ""}
          </span>
        )}
      </label>
    </div>
  );
}

type TradeIntent = "investment" | "short_term";

/** Approve/Reject card; short-term buys can set optional SL/TP before Approve. */
function PendingTradeCard({
  trades,
  disabled,
  onApprove,
  onReject,
}: {
  trades: TradeRequest[];
  disabled: boolean;
  onApprove: (exits: ExitPlan[]) => void;
  onReject: () => void;
}) {
  const buyIndexes = trades
    .map((t, i) => (isBuyTrade(t) ? i : -1))
    .filter((i) => i >= 0);
  const hasBuys = buyIndexes.length > 0;
  const buyTickers = [
    ...new Set(
      buyIndexes
        .map((i) => tradeTicker(trades[i]))
        .filter((t): t is string => !!t)
    ),
  ];
  const buyTickersKey = buyTickers.join(",");

  // Default Investment = no SL/TP (opt-in via Short-term trade)
  const [intent, setIntent] = useState<TradeIntent>("investment");
  const [okByIndex, setOkByIndex] = useState<Record<number, boolean>>({});
  const plansRef = useRef<Record<number, ExitPlan | null>>({});
  const [livePrices, setLivePrices] = useState<Record<string, number>>({});
  const [priceErrors, setPriceErrors] = useState<Record<string, string>>({});
  const [flashes, setFlashes] = useState<Record<string, PriceFlash>>({});
  const prevPrices = useRef<Record<string, number>>({});

  // Live spot every ~3s — same /getprice path as Charts
  useEffect(() => {
    if (!buyTickersKey) {
      setLivePrices({});
      setPriceErrors({});
      setFlashes({});
      prevPrices.current = {};
      return;
    }
    const tickers = buyTickersKey.split(",").filter(Boolean);
    let cancelled = false;
    prevPrices.current = {};
    setLivePrices({});
    setPriceErrors({});
    setFlashes({});

    async function loadPrices() {
      await Promise.all(
        tickers.map(async (ticker) => {
          try {
            const res = await fetch(`${API_BASE}/getprice/${ticker}`);
            const data = await res.json();
            if (cancelled) return;
            if (!res.ok) {
              setPriceErrors((prev) => ({
                ...prev,
                [ticker]:
                  typeof data.detail === "string"
                    ? data.detail
                    : "Could not load price",
              }));
              return;
            }
            const next = Number(data.price);
            if (!Number.isFinite(next) || next <= 0) {
              setPriceErrors((prev) => ({
                ...prev,
                [ticker]: "Could not load price",
              }));
              return;
            }
            const old = prevPrices.current[ticker];
            if (old != null && next !== old) {
              const dir: PriceFlash = next > old ? "up" : "down";
              setFlashes((f) => ({ ...f, [ticker]: dir }));
              window.setTimeout(() => {
                setFlashes((f) =>
                  f[ticker] === dir ? { ...f, [ticker]: "" } : f
                );
              }, 700);
            }
            prevPrices.current[ticker] = next;
            setLivePrices((p) => ({ ...p, [ticker]: next }));
            setPriceErrors((prev) => {
              if (!prev[ticker]) return prev;
              const cleared = { ...prev };
              delete cleared[ticker];
              return cleared;
            });
          } catch {
            if (!cancelled) {
              setPriceErrors((prev) => ({
                ...prev,
                [ticker]: "Could not load price",
              }));
            }
          }
        })
      );
    }

    void loadPrices();
    const id = window.setInterval(() => void loadPrices(), 3000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [buyTickersKey]);

  const shortTerm = intent === "short_term";
  const exitsOk =
    !shortTerm || buyIndexes.every((i) => okByIndex[i] !== false);

  return (
    <div className="trade-card">
      <div className="trade-card__label">Pending trade</div>
      {trades.map((t, i) => (
        <div key={i} className="trade-card__row">
          <div className="trade-card__detail">{tradeLabel(t)}</div>
        </div>
      ))}

      {hasBuys && (
        <div className="trade-card__intent" role="group" aria-label="Trade type">
          <span className="trade-card__intent-label">Trade type</span>
          <div className="trade-card__seg">
            <button
              type="button"
              className={`trade-card__seg-btn${intent === "investment" ? " is-active" : ""}`}
              disabled={disabled}
              onClick={() => {
                setIntent("investment");
                plansRef.current = {};
              }}
            >
              Investment
            </button>
            <button
              type="button"
              className={`trade-card__seg-btn${intent === "short_term" ? " is-active" : ""}`}
              disabled={disabled}
              onClick={() => setIntent("short_term")}
            >
              Short-term trade
            </button>
          </div>

          {buyTickers.map((ticker) => {
            const px = livePrices[ticker];
            const flash = flashes[ticker] || "";
            const err = priceErrors[ticker];
            return (
              <p
                key={ticker}
                className={
                  flash
                    ? `trade-card__live is-flash-${flash}`
                    : "trade-card__live"
                }
              >
                {px != null ? (
                  <>
                    Live: ${formatLivePrice(px)}
                    {buyTickers.length > 1 ? (
                      <span className="trade-card__live-ticker"> {ticker}</span>
                    ) : null}
                  </>
                ) : err ? (
                  <span className="trade-card__exit-error">{err}</span>
                ) : (
                  <>Live: …</>
                )}
              </p>
            );
          })}

          <p className="trade-card__intent-hint">
            {shortTerm
              ? "Set a stop loss and/or take profit (optional)."
              : "Hold without exits — no stop loss or take profit."}
          </p>
        </div>
      )}

      {shortTerm &&
        buyIndexes.map((i) => {
          const ticker = tradeTicker(trades[i]);
          return (
            <TradeExitFields
              key={i}
              trade={trades[i]}
              disabled={disabled}
              livePrice={ticker ? livePrices[ticker] ?? null : null}
              priceError={
                ticker ? priceErrors[ticker] : "Missing ticker"
              }
              onValidityChange={(ok) =>
                setOkByIndex((prev) =>
                  prev[i] === ok ? prev : { ...prev, [i]: ok }
                )
              }
              onPlanChange={(plan) => {
                plansRef.current[i] = plan;
              }}
            />
          );
        })}

      <div className="trade-card__actions">
        <button
          type="button"
          className="btn-approve"
          disabled={disabled || !exitsOk}
          onClick={() => {
            if (!shortTerm) {
              onApprove([]);
              return;
            }
            const exits = buyIndexes
              .map((i) => plansRef.current[i])
              .filter((p): p is ExitPlan => p != null);
            onApprove(exits);
          }}
        >
          Approve
        </button>
        <button
          type="button"
          className="btn-reject"
          disabled={disabled}
          onClick={onReject}
        >
          Reject
        </button>
      </div>
    </div>
  );
}

export function Chat() {
  const { user, loading, accessToken } = useAuth();
  const api = useApi();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [bootError, setBootError] = useState("");
  const streamRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const resolvingRef = useRef(false);
  const [chartTicker, setChartTicker] = useState<string | null>(null);
  const [limitNotice, setLimitNotice] = useState("");

  const atChatLimit = conversations.length >= MAX_CHATS;
  const atMessageLimit = messages.length >= MAX_MESSAGES;

  // Phones start with the history drawer closed so chat has full width
  useEffect(() => {
    if (window.matchMedia("(max-width: 860px)").matches) {
      setSidebarOpen(false);
    }
  }, []);

  useEffect(() => {
    const el = streamRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, typing]);

  useEffect(() => {
    if (atMessageLimit) {
      setLimitNotice(MESSAGE_LIMIT_MSG);
    } else {
      setLimitNotice((n) => (n === MESSAGE_LIMIT_MSG ? "" : n));
    }
  }, [atMessageLimit]);

  const refreshConversations = useCallback(async () => {
    const rows = (await api.get("/chat/conversations")) as Conversation[];
    setConversations(rows);
    return rows;
  }, [api]);

  const loadConversation = useCallback(
    async (id: string) => {
      setActiveId(id);
      setLimitNotice("");
      if (window.matchMedia("(max-width: 860px)").matches) {
        setSidebarOpen(false);
      }
      const rows = (await api.get(`/chat/conversations/${id}/messages`)) as Message[];
      // Only the newest pending trade should show Approve/Reject
      let sawPending = false;
      const cleaned = [...rows].reverse().map((m) => {
        const meta = { ...(m.metadata || {}) };
        const hasPending = !!meta.pending_trades?.length && !meta.resolved;
        if (hasPending) {
          if (sawPending) {
            meta.pending_trades = [];
            meta.resolved = true;
            // Don't fake "Approved" — just hide the buttons
            meta.resolution = meta.resolution || "cancelled";
          } else {
            sawPending = true;
          }
        }
        return { ...m, metadata: meta };
      });
      setMessages(cleaned.reverse());
    },
    [api]
  );

  const startNewChat = useCallback(async () => {
    if (conversations.length >= MAX_CHATS) {
      setLimitNotice(CHAT_LIMIT_MSG);
      return;
    }
    try {
      const created = (await api.post("/chat/conversations", {
        title: "New chat",
      })) as Conversation;
      await refreshConversations();
      setActiveId(created.id);
      setMessages([]);
      setLimitNotice("");
      if (window.matchMedia("(max-width: 860px)").matches) {
        setSidebarOpen(false);
      }
    } catch (e) {
      setLimitNotice(e instanceof Error ? e.message : CHAT_LIMIT_MSG);
    }
  }, [api, refreshConversations, conversations.length]);

  useEffect(() => {
    if (!user || !accessToken) return;
    (async () => {
      try {
        setBootError("");
        const rows = await refreshConversations();
        if (rows.length) {
          await loadConversation(rows[0].id);
        } else {
          await startNewChat();
        }
      } catch (e) {
        setBootError(e instanceof Error ? e.message : "Failed to load chats");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, accessToken]);

  if (loading) {
    return (
      <div className="page chat-page chat-page--center">
        <p className="chat-boot">Loading desk…</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  function resizeTa() {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 140)}px`;
  }

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || typing) return;

    if (messages.length >= MAX_MESSAGES) {
      setLimitNotice(MESSAGE_LIMIT_MSG);
      return;
    }

    let convoId = activeId;
    if (!convoId) {
      if (conversations.length >= MAX_CHATS) {
        setLimitNotice(CHAT_LIMIT_MSG);
        return;
      }
      try {
        const created = (await api.post("/chat/conversations", {
          title: "New chat",
        })) as Conversation;
        convoId = created.id;
        setActiveId(convoId);
        await refreshConversations();
      } catch (e) {
        setLimitNotice(e instanceof Error ? e.message : CHAT_LIMIT_MSG);
        return;
      }
    }

    // Cancel any open Approve/Reject when the user types something new
    setMessages((m) =>
      m.map((row) =>
        row.metadata?.pending_trades?.length && !row.metadata?.resolved
          ? {
              ...row,
              metadata: {
                ...row.metadata,
                pending_trades: [],
                resolved: true,
                resolution: "cancelled",
              },
            }
          : row
      )
    );

    const localUser: Message = {
      id: `local-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    setMessages((m) => [...m, localUser]);
    setInput("");
    setTyping(true);
    requestAnimationFrame(resizeTa);

    // If they asked for a price, attach a "See it live" chart link
    const priceTicker = detectPriceTicker(trimmed);
    const streamId = `stream-${Date.now()}`;
    let sawToken = false;
    let gotFinal = false;
    let streamError = "";

    try {
      await api.streamChat(
        `/chat/conversations/${convoId}/messages/stream`,
        { message: trimmed },
        (event) => {
          if (event.type === "token") {
            if (!sawToken) {
              sawToken = true;
              // First token → swap typing dots for a live bubble
              setTyping(false);
              setMessages((m) => [
                ...m,
                {
                  id: streamId,
                  role: "assistant",
                  content: event.text,
                  metadata: priceTicker ? { chart_ticker: priceTicker } : {},
                },
              ]);
            } else {
              setMessages((m) =>
                m.map((row) =>
                  row.id === streamId
                    ? { ...row, content: row.content + event.text }
                    : row
                )
              );
            }
            return;
          }

          if (event.type === "error") {
            streamError = event.detail || "Stream error";
            return;
          }

          if (event.type === "final") {
            gotFinal = true;
            setTyping(false);
            const assistant: Message = {
              id: event.message?.id || streamId,
              role: "assistant",
              content: event.reply || "",
              metadata: {
                pending_trades: event.pending_trades || [],
                ...(priceTicker ? { chart_ticker: priceTicker } : {}),
              },
            };
            setMessages((m) => {
              const idx = m.findIndex((row) => row.id === streamId);
              if (idx >= 0) {
                const next = [...m];
                next[idx] = assistant;
                return next;
              }
              return [...m, assistant];
            });
            setLimitNotice("");
          }
        }
      );

      if (streamError) {
        throw new Error(streamError);
      }
      if (!gotFinal) {
        throw new Error("Stream ended without a reply");
      }
      await refreshConversations();
    } catch (e) {
      const err = e instanceof Error ? e.message : "Something went wrong";
      setTyping(false);
      // Roll back the optimistic user bubble on limit errors
      if (err.includes("Message limit") || err.includes("Chat limit")) {
        setMessages((m) =>
          m.filter((row) => row.id !== localUser.id && row.id !== streamId)
        );
        setLimitNotice(err);
      } else {
        setMessages((m) => {
          const withoutStream = m.filter((row) => row.id !== streamId);
          return [
            ...withoutStream,
            {
              id: `err-${Date.now()}`,
              role: "assistant",
              content: err,
            },
          ];
        });
      }
    } finally {
      setTyping(false);
    }
  }

  async function resolveTrades(
    messageId: string,
    approve: boolean,
    exits: ExitPlan[] = []
  ) {
    if (!activeId || typing || resolvingRef.current) return;
    const msg = messages.find((m) => m.id === messageId);
    const pending = msg?.metadata?.pending_trades || [];
    if (!pending.length || msg?.metadata?.resolved) return;

    resolvingRef.current = true;

    // Hide buttons on every pending card in this chat
    setMessages((prev) =>
      prev.map((m) =>
        m.metadata?.pending_trades?.length && !m.metadata?.resolved
          ? {
              ...m,
              metadata: {
                ...m.metadata,
                pending_trades: [],
                resolved: true,
                resolution: approve ? "approve" : "reject",
              },
            }
          : m
      )
    );
    setTyping(true);

    try {
      const decisions = pending.map(() =>
        approve
          ? { type: "approve" }
          : { type: "reject", message: "User said no. Do not retry this trade." }
      );
      const turn = await api.post(`/chat/conversations/${activeId}/resume`, {
        decisions,
      });

      const raw = turn.reply ? String(turn.reply).trim() : "";
      const stub = !raw || raw.toLowerCase() === "response submitted";
      let reply = stub
        ? approve
          ? "Trade approved and submitted."
          : "Trade rejected. Nothing was sent."
        : raw;

      // After a successful buy approve, set any SL/TP the user chose (short-term)
      if (approve && exits.length > 0) {
        // Brief pause so the market buy can fill before /paper/exits checks holdings
        await new Promise((r) => setTimeout(r, 600));
        const exitNotes: string[] = [];
        for (const plan of exits) {
          try {
            const body: Record<string, unknown> = { ticker: plan.ticker };
            if (plan.stop_loss != null) body.stop_loss = plan.stop_loss;
            if (plan.take_profit != null) body.take_profit = plan.take_profit;
            if (plan.qty != null) body.qty = plan.qty;
            await api.post("/paper/exits", body);
            const parts: string[] = [];
            if (plan.stop_loss != null) parts.push(`SL $${plan.stop_loss}`);
            if (plan.take_profit != null) parts.push(`TP $${plan.take_profit}`);
            exitNotes.push(`${plan.ticker}: ${parts.join(", ")}`);
          } catch (err) {
            const detail =
              err instanceof Error ? err.message : "Could not set exits";
            exitNotes.push(`${plan.ticker} exits failed: ${detail}`);
          }
        }
        if (exitNotes.length) {
          reply = `${reply}\n\nExits: ${exitNotes.join(" · ")}`;
        }
      }

      const followUpPending = turn.pending_trades || [];

      setMessages((m) => [
        ...m.map((row) =>
          row.metadata?.resolved || row.id === messageId
            ? {
                ...row,
                metadata: {
                  ...row.metadata,
                  pending_trades: [],
                  resolved: true,
                  resolution:
                    row.metadata?.resolution || (approve ? "approve" : "reject"),
                },
              }
            : row
        ),
        {
          id: turn.message?.id || `r-${Date.now()}`,
          role: "assistant",
          content: reply,
          metadata: {
            pending_trades: followUpPending,
            resolved: false,
          },
        },
      ]);
      await refreshConversations();
    } catch (e) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId
            ? {
                ...m,
                metadata: {
                  ...m.metadata,
                  pending_trades: pending,
                  resolved: false,
                  resolution: undefined,
                },
              }
            : m
        )
      );
      setMessages((m) => [
        ...m,
        {
          id: `err-${Date.now()}`,
          role: "assistant",
          content: e instanceof Error ? e.message : "Resume failed",
        },
      ]);
    } finally {
      resolvingRef.current = false;
      setTyping(false);
    }
  }

  async function removeConversation(id: string) {
    await api.del(`/chat/conversations/${id}`);
    const rows = await refreshConversations();
    setLimitNotice("");
    if (activeId === id) {
      if (rows[0]) {
        await loadConversation(rows[0].id);
      } else if (rows.length < MAX_CHATS) {
        await startNewChat();
      } else {
        setActiveId(null);
        setMessages([]);
      }
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(input);
    }
  }

  return (
    <div className={`page chat-layout${sidebarOpen ? "" : " chat-layout--collapsed"}`}>
      {sidebarOpen && (
        <button
          type="button"
          className="chat-sidebar__backdrop"
          aria-label="Close sidebar"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside className="chat-sidebar">
        <div className="chat-sidebar__top">
          <button
            type="button"
            className="btn btn--primary chat-sidebar__new"
            onClick={() => void startNewChat()}
            disabled={atChatLimit}
            title={atChatLimit ? CHAT_LIMIT_MSG : "Start a new chat"}
          >
            New chat
          </button>
          <Link to="/" className="chat-sidebar__toggle" aria-label="Home" title="Home">
            ⌂
          </Link>
          <button
            type="button"
            className="chat-sidebar__toggle"
            onClick={() => setSidebarOpen(false)}
            aria-label="Collapse sidebar"
          >
            ←
          </button>
        </div>
        <p className="chat-sidebar__caps">
          {conversations.length}/{MAX_CHATS} chats
          {activeId ? ` · ${Math.min(messages.length, MAX_MESSAGES)}/${MAX_MESSAGES} msgs` : ""}
        </p>
        {atChatLimit && (
          <p className="chat-sidebar__limit">Delete a chat to open a new one.</p>
        )}
        <ul className="chat-sidebar__list">
          {conversations.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className={`chat-sidebar__item${c.id === activeId ? " is-active" : ""}`}
                onClick={() => void loadConversation(c.id)}
              >
                <span>{c.title || "New chat"}</span>
              </button>
              <button
                type="button"
                className="chat-sidebar__delete"
                aria-label="Delete chat"
                onClick={() => void removeConversation(c.id)}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {!sidebarOpen && (
        <button
          type="button"
          className="chat-sidebar__open"
          onClick={() => setSidebarOpen(true)}
          aria-label="Open sidebar"
        >
          ☰
        </button>
      )}

      <div className="chat-page">
        <header className="chat-header">
          <div className="chat-header__left">
            <img src="/signal-s.png" alt="" className="chat-header__icon" />
            <div>
              <h1 className="brand-name">Signal Gate</h1>
              <p>Paper mode</p>
            </div>
          </div>
          <div className="chat-header__right">
            <div className="chat-status">
              <span className="chat-status__dot" />
              Live
            </div>
            <UserMenu />
          </div>
        </header>

        {bootError && (
          <div className="chat-boot-error">
            {bootError}. Make sure Supabase is linked and the API is running.{" "}
            <Link to="/login">Back to login</Link>
          </div>
        )}

        <div className="chat-stream" ref={streamRef}>
          {messages.length === 0 && !typing && (
            <div className="chat-empty">
              <img src="/signal-s.png" alt="" />
              <h2>What should we move?</h2>
              <p>
                Prices, research, portfolio checks, or paper trades — saved to your
                sidebar automatically.
              </p>
              <div className="chat-suggestions">
                {suggestions.map((s) => (
                  <button key={s} type="button" onClick={() => void send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          <AnimatePresence initial={false}>
            {messages.map((m, index) => {
              const liveTicker =
                m.metadata?.chart_ticker ||
                (m.role === "assistant" && messages[index - 1]?.role === "user"
                  ? detectPriceTicker(messages[index - 1].content)
                  : null);

              return (
              <motion.div
                key={m.id}
                className={`msg msg--${m.role}`}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
              >
                {m.role === "assistant" && (
                  <img src="/signal-s.png" alt="" className="msg__avatar" />
                )}
                <div className="msg__stack">
                  {m.role === "assistant" && (
                    <span className="brand-name msg__name">Signal Gate</span>
                  )}
                  <div className="msg__bubble">
                    {m.content}
                    {m.role === "assistant" && liveTicker && (
                      <button
                        type="button"
                        className="msg__live"
                        onClick={() => setChartTicker(liveTicker)}
                      >
                        See it live →
                      </button>
                    )}
                    {!!m.metadata?.pending_trades?.length && !m.metadata?.resolved && (
                      <PendingTradeCard
                        trades={m.metadata.pending_trades}
                        disabled={typing}
                        onApprove={(exits) =>
                          void resolveTrades(m.id, true, exits)
                        }
                        onReject={() => void resolveTrades(m.id, false)}
                      />
                    )}
                    {m.metadata?.resolved &&
                      (m.metadata.resolution === "approve" ||
                        m.metadata.resolution === "reject") && (
                      <div className="trade-card trade-card--done">
                        <div className="trade-card__detail" style={{ marginBottom: 0 }}>
                          {m.metadata.resolution === "reject"
                            ? "Rejected"
                            : "Approved ✓"}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
              );
            })}
          </AnimatePresence>

          {typing && (
            <div className="msg msg--assistant msg--typing">
              <img src="/signal-s.png" alt="" className="msg__avatar" />
              <div className="msg__bubble">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}
        </div>

        <form className="chat-composer" onSubmit={onSubmit}>
          {(limitNotice || atMessageLimit) && (
            <div className="chat-limit-banner" role="status">
              <p>{limitNotice || MESSAGE_LIMIT_MSG}</p>
              {atMessageLimit && activeId && (
                <button
                  type="button"
                  className="chat-limit-banner__action"
                  onClick={() => void removeConversation(activeId)}
                >
                  Delete this chat
                </button>
              )}
            </div>
          )}
          <div className="chat-composer__box">
            <textarea
              ref={taRef}
              rows={1}
              placeholder={
                atMessageLimit
                  ? "Message limit reached — delete this chat to continue"
                  : "Ask Signal Gate anything…"
              }
              value={input}
              disabled={atMessageLimit || typing}
              onChange={(e) => {
                setInput(e.target.value);
                resizeTa();
              }}
              onKeyDown={onKeyDown}
            />
            <button
              type="submit"
              className="chat-composer__send"
              disabled={!input.trim() || typing || atMessageLimit}
              aria-label="Send"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 19V5M12 5l-6 6M12 5l6 6"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
          <p className="chat-composer__hint">
            {atMessageLimit
              ? "Delete this chat and open a new one"
              : "Enter to send · Shift+Enter for new line"}
          </p>
          <p className="chat-composer__credit">
            Made by <span className="credit-name">WaffeDevs</span>
            <span className="chat-composer__sep">·</span>
            <a href="https://www.linkedin.com/in/ayaanalii/" target="_blank" rel="noreferrer">
              LinkedIn
            </a>
            <span className="chat-composer__sep">·</span>
            <a href="https://github.com/WafflesDevs" target="_blank" rel="noreferrer">
              GitHub
            </a>
          </p>
        </form>
      </div>

      <ChartSidebar ticker={chartTicker} onClose={() => setChartTicker(null)} />
    </div>
  );
}
