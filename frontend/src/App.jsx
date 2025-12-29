import React, { useState, useEffect, useRef } from 'react';
function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);      //state for loading indicator
  const [trace, setTrace] = useState(null);               //state for agent logs
  const scrollRef = useRef(null);
  const [logicTrace, setLogicTrace] = useState("");
  const [displayBuffer, setDisplayBuffer] = useState("");
  const logicEndRef = useRef(null);
  
  // Typewriter effect component for terminal output
  const TypewriterTerminal = ({ text }) => {
    return (
      <span className="text-emerald-500/90 inline-block">
        {text || "> System idle. Awaiting command..."}
        <span className="ml-1 inline-block w-1 h-3 bg-emerald-500 animate-terminal-blink align-middle" />
      </span>
    );
  };

  //  Logic trace: Function to scroll to the bottom of the logic console
  const scrollToBottom = () => {
    logicEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Logic trace: Auto-scroll whenever logicTrace updates
  useEffect(() => {
  if (displayBuffer.length > 0) {
    const timeout = setTimeout(() => {
      setLogicTrace(prev => prev + displayBuffer[0]);
      setDisplayBuffer(prev => prev.slice(1));
    }, 4); // Adjust this for typing speed (ms per character)
    return () => clearTimeout(timeout);
  }
}, [displayBuffer, logicTrace]);

  // Main text box: Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    // Add user message to UI immediately
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    setTrace(null);
    setLogicTrace("");
    setDisplayBuffer("> Initializing Orchestrator Link...");

    try {
      // Call FastAPI backend on port 8001
      const response = await fetch('http://18.189.246.165:8001/chat_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: input,               
          user_id: "default_user",
          session_id: "session_1" 
        }),
      });

      // handle streaming reader
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n\n");

          lines.forEach(line => {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.replace("data: ", ""));

                const newEntry = `\n[${data.agent}] ${data.content}`;
                setDisplayBuffer(prev => prev + newEntry);

                // Update Sidebar Trace
                if (data.trace_data) {
                  setTrace(data.trace_data);
                }

                // If it's the final result, add it to the chat messages
                if (data.type === "final") {
                  setMessages(prev => [...prev, { role: 'agent', content: data.content }]);
                }
              } catch (e) {
                console.error("Error parsing SSE chunk:", e);
              }
            }
          });
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'error', content: "Kernel link failed." }]);
      setLogicTrace(prev => {
        const time = new Date().toLocaleTimeString([], { hour12: false, minute: '2-digit', second: '2-digit' });
        return prev + `[${time}] [${data.type.toUpperCase()}] ${data.content}\n`;
      });
    } finally {
      setIsLoading(false); 
    }
  };
  return (
  <div className="flex h-screen bg-[#0a0a0a] text-zinc-100 font-sans">
     {/* Main Chat Side */}
      <div className="flex-1 flex flex-col border-r border-zinc-800/50">
        <header className="py-6 px-4 border-b border-zinc-800/50 bg-[#0a0a0a]/80 backdrop-blur-md text-center">
          <h1 className="text-xl font-semibold tracking-tight">Smart Audit</h1>
          <p className="text-[10px] text-zinc-500 uppercase tracking-[0.2em] mt-1">Orchestrator Prototype</p>
        </header>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-8 space-y-6">
          <div className="max-w-2xl mx-auto w-full space-y-8">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-4 py-3 rounded-2xl text-[15px] shadow-sm ${
                  msg.role === 'user' ? 'bg-blue-600 text-white rounded-br-none' : 'bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-bl-none'
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}
            {isLoading && <div className="text-xs text-zinc-500 animate-pulse">Orchestrator invoking agents...</div>}
            <div ref={scrollRef} />
          </div>
        </div>
        
        {/* Input Area */}
        <div className="p-4">
          <div className="max-w-2xl mx-auto relative group">
            <div className="relative flex items-center bg-zinc-900 border border-zinc-800 rounded-2xl p-2 pl-4">
              <input
                className="flex-1 bg-transparent border-none outline-none text-sm py-2"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Talk to the system..."
              />
              <button className="ml-2 px-4 py-2 bg-white text-black rounded-xl text-sm font-bold" onClick={handleSend}>
                Send
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* System Trace Sidebar */}
      <div className="w-80 bg-[#0d0d0d] p-6 hidden lg:block overflow-y-auto border-l border-zinc-800">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xs font-bold text-blue-500 uppercase tracking-widest">Agent Trace</h2>
          {isLoading && <span className="flex h-2 w-2 rounded-full bg-blue-500 animate-ping"></span>}
        </div>

        {/* Only show "System Idle" if there is no trace AND we aren't currently loading */}
        {!trace && !isLoading ? (
          <div className="h-40 flex items-center justify-center border border-dashed border-zinc-800 rounded-lg">
            <p className="text-zinc-600 text-xs italic">System Idle</p>
          </div>
        ) : (
        <div className="space-y-6">
          {/* 01: Memory Hit - Shown as soon as MemoryAgent yields */}
          <TraceItem 
            step="01" 
            label="Memory Hit" 
            value={trace?.memory_context || (isLoading ? "Searching World Model..." : "N/A")} 
            color="text-emerald-400" 
          />

          {/* 02: Domain - Population from MatchingAgent */}
          <TraceItem 
            step="02" 
            label="Domain Classification" 
            value={trace?.domain || (isLoading ? "Classifying Intent..." : "N/A")} 
            color="text-amber-400" 
          />

          {/* 03: Confidence Score */}
          <TraceItem 
            step="03" 
            label="Confidence" 
            value={trace?.score ? `${(trace.score * 100).toFixed(1)}%` : (isLoading ? "Calculating..." : "0%")} 
            color="text-purple-400" 
          />

          {/* 04: Grounded Value */}
          <TraceItem 
            step="04" 
            label="Actual Value" 
            value={trace?.actual_value !== undefined ? trace.actual_value : (isLoading ? "Auditing..." : "N/A")} 
            color="text-cyan-400" 
          />
        </div>
      )}
      
      {/* The Backend Execution Kernel - Placed below for visual hierarchy */}
      <div className="mt-8 pt-6 border-t border-zinc-800/60">
        {/* Header with status pulse */}
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
            Execution Kernel
          </h3>
          {isLoading && (
            <span className="text-[9px] text-emerald-500/70 font-mono animate-pulse">
              LIVE_ACCESS_GRANTED
            </span>
          )}
        </div>

        {/* Terminal Window */}
        <div className="group relative">
          {/* Subtle Glow Effect */}
          <div className="absolute -inset-0.5 bg-emerald-500/5 rounded opacity-0 group-hover:opacity-100 transition duration-500"></div>
          
          <div className="relative bg-[#050505] rounded-md p-4 font-mono text-[10px] border border-zinc-800/80 shadow-2xl overflow-hidden">
            {/* Scanline Overlay Effect */}
            <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.02),rgba(0,255,0,0.01),rgba(0,0,255,0.02))] bg-[length:100%_2px,3px_100%] z-10"></div>

            <div className="flex flex-col gap-1.5 overflow-y-auto max-h-72 custom-scrollbar relative z-0">
              <pre className="whitespace-pre-wrap leading-relaxed break-all">
                <span className="text-zinc-600 mr-2">
                  [{new Date().toLocaleTimeString([], {hour12: false})}]
                </span>
                <TypewriterTerminal text={logicTrace} />
              </pre>
              <div ref={logicEndRef} />
            </div>  

            {/* Terminal Footer */}
            <div className="mt-3 pt-2 border-t border-zinc-900 flex justify-between items-center opacity-40">
              <span className="text-[8px] text-zinc-600 uppercase">Process: ADK_Runner_v1</span>
              <span className="text-[8px] text-zinc-600">UTF-8</span>
            </div>
          </div>
        </div>
      </div>
      </div>
  </div>
  );
}

function TraceItem({ step, label, value, color }) {
  return (
    <div className="group relative">
      <div className="absolute -left-[17px] top-1 text-[8px] font-bold text-zinc-700">{step}</div>
      <div className="space-y-1.5 border-l border-zinc-800 pl-4 group-hover:border-blue-500/50 transition-colors">
        <p className="text-[9px] text-zinc-500 uppercase font-black tracking-widest">{label}</p>
        <p className={`text-sm font-mono ${color} break-words leading-tight`}>
          {value || "Processing..."}
        </p>
      </div>
    </div>
  );
}

export default App;