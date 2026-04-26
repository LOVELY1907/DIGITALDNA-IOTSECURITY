import React, { useEffect, useState, useRef } from "react";
import io from "socket.io-client";
import "./App.css";
// Icons for alerts & activities
const AlertIcon = () => (
  <span style={{ color: "#ff4d6d", marginRight: 6, fontSize: 16 }}>
    ⚠️
  </span>
);

const ActivityIcon = () => (
  <span style={{ color: "#00eaff", marginRight: 6, fontSize: 16 }}>
    📘
  </span>
);

const SERVER_BASE = "http://172.20.10.2:5001";
const socket = io(SERVER_BASE, { transports: ["websocket", "polling"] });

function formatTime(ts) {
  if (!ts) return "--";
  const d = new Date(ts > 1e10 ? ts : ts * 1000);
  return isNaN(d.getTime()) ? "--" : d.toLocaleTimeString();
}

function NodeItem({ node, onSelect }) {
  const status = (node.status || "SAFE").toUpperCase();
  const cpu = node.telemetry?.cpu;
  const bright = node.telemetry?.brightness;

  return (
    <div className="nodeItem" onClick={onSelect}>
      <div className="nodeInfo">
        <div className="nodeName">{node.node_id}</div>
        <div className="nodeIdSmall">
  DNA: {node.dna ? node.dna.slice(0, 20) + "…" : "—"}
</div>
      </div>

      <div style={{ textAlign: "right" }}>
        <div className={status === "COMPROMISED" ? "nodeStatusBad" : "nodeStatusSafe"}>
          {status}
        </div>
        <div className="smallMuted">
          CPU {cpu ? Math.round(cpu) : "--"}% •{" "}
          {bright ? Math.round(bright * 100) : "--"}%
        </div>

        {status === "COMPROMISED" && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              fetch(`${SERVER_BASE}/quarantine`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: node.node_id }),
              })
                .then((r) => r.json())
                .then(() => alert("QUARANTINED " + node.node_id));
            }}
            style={{
              marginTop: 6,
              padding: "4px 8px",
              fontSize: 10,
              background: "#ff4c68",
              color: "white",
              borderRadius: "6px",
              border: "none",
              cursor: "pointer",
              boxShadow: "0 0 6px red",
            }}
          >
            QUARANTINE
          </button>
        )}
        
      </div>
    </div>
  );
}

function NodeStatusMap({ nodes, selectedId, onSelect }) {
  const list = Object.values(nodes);
  if (!list.length) return <div className="mapEmpty smallMuted">No nodes yet</div>;

  return (
    <div className="mapGrid">
      {list.map((n) => (
        <div
          key={n.node_id}
          className={
            "mapNode " +
            ((n.status || "SAFE").toUpperCase() === "COMPROMISED" ? "mapNodeBad " : "mapNodeSafe ") +
            (selectedId === n.node_id ? "mapNodeSelected" : "")
          }
          onClick={() => onSelect(n.node_id)}
        >
          <div className="mapNodeName">{n.node_id}</div>
          <div className="mapNodeStatus">
            {(n.status || "SAFE").toUpperCase() === "COMPROMISED" ? "COMP" : "SAFE"}
          </div>
        </div>
      ))}
    </div>
  );
}

function App() {
  const [nodes, setNodes] = useState({});
  const [selectedId, setSelectedId] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [activities, setActivities] = useState([]);

  const [frameUrl, setFrameUrl] = useState(null);
  const imgRef = useRef(null);

  // AI Chat states
  const [aiInput, setAiInput] = useState("");
  const [aiChat, setAiChat] = useState([]);

  function askAI() {
    if (!aiInput.trim()) return;

    // Add user message
    setAiChat((old) => [...old, { from: "user", text: aiInput }]);

    fetch(`${SERVER_BASE}/ai_query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: aiInput }),
    })
      .then((r) => r.json())
      .then((js) => {
        setAiChat((old) => [...old, { from: "bot", text: js.response }]);
      })
      .catch(() => {
        setAiChat((old) => [...old, { from: "bot", text: "AI error" }]);
      });

    setAiInput("");
  }
  // Load existing devices
  useEffect(() => {
    fetch(`${SERVER_BASE}/devices`)
      .then((r) => r.json())
      .then((js) => {
        const formatted = {};
        Object.entries(js || {}).forEach(([id, data]) => {
          formatted[id] = { ...data, node_id: id };
        });
        setNodes(formatted);
      });
  }, []);

  // Live socket updates
  useEffect(() => {
    socket.on("node_update", ({ node_id, data }) => {
      setNodes((prev) => ({
        ...prev,
        [node_id]: { ...(prev[node_id] || {}), ...data, node_id },
      }));

      if ((data.status || "").toUpperCase() === "COMPROMISED") {
        setAlerts((old) => [
          { ts: Date.now(), text: `${node_id} COMPROMISED` },
          ...old,
        ]);
      }
      setActivities((old) => [
  {
    ts: Date.now(),
    text: `${node_id} → ${data.status || "UPDATED"}`,
  },
  ...old,
].slice(0, 50));
    });

    return () => socket.off("node_update");
  }, []);

  // Auto-select first node
  useEffect(() => {
    const ids = Object.keys(nodes);
    if (!selectedId && ids.length) setSelectedId(ids[0]);
  }, [nodes, selectedId]);

  // Set camera frame URL
  useEffect(() => {
    if (!selectedId) {
      setFrameUrl(null);
      return;
    }
    setFrameUrl(`${SERVER_BASE}/frames/${selectedId}.jpg`);
  }, [selectedId]);

  // Refresh image
  useEffect(() => {
    if (!frameUrl) return;
    const img = imgRef.current;

    const refresh = () => {
      if (img) img.src = `${frameUrl}?t=${Date.now()}`;
    };

    refresh();
    const id = setInterval(refresh, 1200);
    return () => clearInterval(id);
  }, [frameUrl]);

  const selected = selectedId ? nodes[selectedId] : null;

  const cpu = selected?.telemetry?.cpu
    ? Math.round(selected.telemetry.cpu)
    : null;

  const temp = selected?.telemetry?.brightness
    ? Math.round(selected.telemetry.brightness * 100)
    : null;

  return (
    <div className="app">

      {/* LEFT SIDE */}
      <div className="left">
        <div className="panel">
          <div className="cameraRow">
            <div className="camBox">
              {frameUrl ? (
                <img ref={imgRef} className="frameImg" alt="live" />
              ) : (
                <div className="camPlaceholder">
                  <div className="h3">LIVE NODE VIEW</div>
                  <div className="smallMuted">Select a node</div>
                </div>
              )}
            </div>

            <div className="statsCol">
              <div className="statCard">
                CPU
                <div className="statValue">
                  {cpu != null ? `${cpu}%` : "--"}
                </div>
              </div>

              <div className="statCard">
                TEMP
                <div className="statValue">{temp != null ? `${temp}°` : "--"}</div>
              </div>

              <div className="statCard">
                LAST
                <div className="statValueSmall">
                  {formatTime(selected?.last_seen)}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* NODE STATUS MAP */}
        <div className="panel" style={{ marginTop: 12 }}>
          <div className="h3">NODE STATUS MAP</div>
          <div className="mapPanel">
            <NodeStatusMap
              nodes={nodes}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>
        </div>
      </div>

      {/* RIGHT SIDE */}
      <div className="right">

        {/* LIVE FEED */}
        <div className="panel" style={{ height: 380 }}>
          <div className="feedHeader">
            <div className="h3">LIVE NODE FEED</div>
            <div className="smallMuted">Auto-updating</div>
          </div>

          <div className="nodeFeedPanel scrollbar">
            {Object.values(nodes).length === 0 && (
              <div className="smallMuted" style={{ padding: 12 }}>
                No nodes yet
              </div>
            )}

            {Object.values(nodes).map((n) => (
              <NodeItem
                key={n.node_id}
                node={n}
                onSelect={() => setSelectedId(n.node_id)}
              />
            ))}
          </div>
        </div>

        <div className="panel" style={{ marginTop: 12 }}>
  <div className="h3">ACTIVITY & ALERTS</div>

  {/* ALERTS */}
  <div className="alertsPanel" style={{ maxHeight: 120, overflowY: "auto" }}>
    {alerts.length === 0 && (
      <div className="smallMuted">No alerts yet</div>
    )}

    {alerts.map((a) => (
      <div key={a.ts} className="alertItem" style={{ display: "flex", gap: 8 }}>
        <AlertIcon />

        <div>
          <div>{a.text}</div>
          <div className="smallMuted">
            {new Date(a.ts).toLocaleTimeString()}
          </div>
        </div>
      </div>
    ))}
  </div>

  {/* ACTIVITIES */}
  <div className="h3" style={{ marginTop: 14 }}>ACTIVITIES</div>

  <div className="alertsPanel" style={{ maxHeight: 140, overflowY: "auto" }}>
    {activities.length === 0 && (
      <div className="smallMuted">No activities yet</div>
    )}

    {activities.map((a, i) => (
      <div key={i} className="alertItem" style={{ display: "flex", gap: 8 }}>
        <ActivityIcon />

        <div>
          <div>{a.text}</div>
          <div className="smallMuted">
            {new Date(a.ts).toLocaleTimeString()}
          </div>
        </div>
      </div>
    ))}
  </div>
</div>

        {/* AI ASSISTANT */}
        <div className="panel assistantBox" style={{ marginTop: 12 }}>
          <div className="h3">AI ASSISTANT</div>

          {/* CHAT WINDOW */}
          <div
            style={{
              background: "rgba(255,255,255,0.05)",
              padding: "10px",
              borderRadius: "8px",
              height: "150px",
              overflowY: "auto",
              marginBottom: "10px",
            }}
          >
            {aiChat.length === 0 && (
              <div className="smallMuted">Ask something…</div>
            )}

            {aiChat.map((m, i) => (
              <div
                key={i}
                style={{
                  marginBottom: "6px",
                  color: m.from === "user" ? "#00eaff" : "white",
                  fontWeight: m.from === "user" ? "bold" : "normal",
                }}
              >
                {m.from === "user" ? "You: " : "AI: "}
                {m.text}
              </div>
            ))}
          </div>

          {/* INPUT ROW */}
          <div style={{ display: "flex", gap: "8px" }}>
            <input
              type="text"
              value={aiInput}
              onChange={(e) => setAiInput(e.target.value)}
              placeholder="Ask AI..."
              style={{
                flex: 1,
                padding: "8px",
                borderRadius: "6px",
                border: "1px solid rgba(255,255,255,0.2)",
                background: "rgba(0,0,0,0.3)",
                color: "white",
              }}
            />
            <button
              onClick={askAI}
              style={{
                padding: "8px 12px",
                borderRadius: "8px",
                background: "#00eaff",
                color: "black",
                fontWeight: "bold",
                cursor: "pointer",
                border: "none",
              }}
            >
              Send
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

export default App;