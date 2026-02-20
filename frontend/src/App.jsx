import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { 
    ShoppingCart, Package, RefreshCw, Search, FileText, Upload, 
    CheckCircle, Clock, ShieldCheck, Boxes, Filter, BarChart3, 
    TrendingUp, CalendarRange, UserCircle, Download, XCircle, 
    Check, Info, FileSpreadsheet, Building2, X, Banknote, 
    Repeat, MessageSquare, Send, Settings, Activity, Terminal, 
    Shield, DollarSign, Zap, ShieldAlert, PieChart as PieIcon,
    AlertTriangle, ArrowRight, Layers, Gavel, Wallet, Eye, 
    Truck, BarChart as BarIcon, Briefcase, Handshake, BrainCircuit
} from 'lucide-react'
import { 
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, 
    ResponsiveContainer, BarChart, Bar, Legend, Cell, PieChart, Pie
} from 'recharts';

function App() {
  // ==========================================
  // 1. STANY I KONFIGURACJA
  // ==========================================
  const [activeTab, setActiveTab] = useState('analytics')
  const [userRole, setUserRole] = useState('manager')
  const [products, setProducts] = useState([])
  const [orders, setOrders] = useState([])
  const [history, setHistory] = useState([]) 
  const [predictions, setPredictions] = useState([]) 
  const [analyticsData, setAnalyticsData] = useState(null)
  const [scenarios, setScenarios] = useState([]) 
  const [simulationStatus, setSimulationStatus] = useState({ current_date: "...", is_running: false, events: [] })
  
  const [delayDays, setDelayDays] = useState(0)
  const [demandSpike, setDemandSpike] = useState(0)
  
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [chatInput, setChatInput] = useState("")
  const [chatMessages, setChatMessages] = useState([{ from: 'bot', text: 'System ERP gotowy do analizy sourcingu.' }])
  const chatEndRef = useRef(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedFile, setSelectedFile] = useState(null)
  const [selectedOrder, setSelectedOrder] = useState(null)
  const [selectedIntervention, setSelectedIntervention] = useState(null) // NOWY STAN DLA XAI
  const [showLowStockOnly, setShowLowStockOnly] = useState(false)

  const API_URL = 'http://127.0.0.1:8000'

  // ==========================================
  // 2. EFEKTY I POBIERANIE DANYCH
  // ==========================================
  useEffect(() => {
    const interval = setInterval(() => {
        fetchSimulationStatus()
        if (activeTab === 'market') fetchProducts()
        if (activeTab === 'orders') fetchOrders()
        if (activeTab === 'analytics') { fetchAnalyticsDashboard(); fetchHistory(); }
        if (activeTab === 'forecast') fetchPredictions()
    }, 2000) 
    return () => clearInterval(interval)
  }, [activeTab])

  useEffect(() => { if (activeTab === 'scenarios') fetchScenarios() }, [delayDays, demandSpike, activeTab])

  const fetchProducts = async (q = "") => { try { const res = await axios.get(`${API_URL}/products?search=${q}`); setProducts(res.data) } catch (e) {} }
  const fetchOrders = async () => { try { const res = await axios.get(`${API_URL}/orders`); setOrders(res.data) } catch (e) {} }
  const fetchHistory = async () => {
    try { 
        const res = await axios.get(`${API_URL}/analytics/history`); 
        setHistory(res.data.map(i => ({...i, shortDate: new Date(i.date).toLocaleDateString(undefined, {month:'numeric', day:'numeric'})}))) 
    } catch (e) {}
  }
  const fetchPredictions = async () => { try { const res = await axios.get(`${API_URL}/analytics/predictions`); setPredictions(res.data) } catch (e) {} }
  const fetchAnalyticsDashboard = async () => { try { const res = await axios.get(`${API_URL}/analytics/dashboard`); setAnalyticsData(res.data) } catch (e) {} }
  const fetchScenarios = async () => { try { const res = await axios.get(`${API_URL}/analytics/what-if?delay_days=${delayDays}&demand_spike=${demandSpike}`); setScenarios(res.data) } catch (e) {} }
  const fetchSimulationStatus = async () => { try { const res = await axios.get(`${API_URL}/simulation/status`); setSimulationStatus(res.data) } catch (e) {} }

  const handleSendMessage = async (e) => {
      e.preventDefault(); if (!chatInput.trim()) return
      const userMsg = chatInput; setChatMessages(prev => [...prev, { from: 'user', text: userMsg }]); setChatInput("")
      try { const res = await axios.post(`${API_URL}/assistant/chat`, { message: userMsg }); setChatMessages(prev => [...prev, { from: 'bot', text: res.data.text }]) } catch (e) {}
  }

  const handleOrder = async (item) => {
    const qty = prompt(`Podaj ilość dla: ${item.product_name || item.name}`, "50")
    if (!qty) return
    try { await axios.post(`${API_URL}/orders`, { product_id: item.id, quantity: parseFloat(qty) }); alert("✅ Zamówienie wysłane!") } catch (e) {}
  }

  const calculateInvoice = (order) => {
    const net = order.total_price / 1.23
    return { net, vat: order.total_price - net, gross: order.total_price }
  }

  return (
    <div className="app-layout">
      
      {/* SIDEBAR */}
      <div className="sidebar">
        <div className="logo-area">
            <div className="logo-box"><Zap size={24} color="#fff" fill="#fff"/></div>
            <div>
                <span className="logo-title">Procurement Pro</span>
                <span className="logo-tag">v5.3.0 AI Enterprise</span>
            </div>
        </div>

        <nav className="side-nav">
            <p className="nav-group-label">LOGISTYKA</p>
            <button className={`nav-item ${activeTab === 'market' ? 'active' : ''}`} onClick={() => setActiveTab('market')}><Search size={18}/> Marketplace AI</button>
            <button className={`nav-item ${activeTab === 'forecast' ? 'active' : ''}`} onClick={() => setActiveTab('forecast')}><Boxes size={18}/> Magazyn MRP</button>
            <button className={`nav-item ${activeTab === 'orders' ? 'active' : ''}`} onClick={() => setActiveTab('orders')}><Truck size={18}/> Monitoring</button>

            <p className="nav-group-label" style={{marginTop:'25px'}}>STRATEGIA</p>
            <button className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')}><BarChart3 size={18}/> Raporty & BI</button>
            <button className={`nav-item ${activeTab === 'contracts' ? 'active' : ''}`} onClick={() => setActiveTab('contracts')}><Wallet size={18}/> Smart Wallet</button>
            <button className={`nav-item ${activeTab === 'scenarios' ? 'active' : ''}`} onClick={() => setActiveTab('scenarios')} style={{color:'#a855f7'}}><Activity size={18}/> Symulacje Risk</button>
        </nav>

        <div className="sidebar-bottom">
            <div className="user-profile">
                <div className="avatar">JD</div>
                <div className="user-text">
                    <span className="user-name">Manager Sourcingu</span>
                    <span className="user-status">Online</span>
                </div>
            </div>
        </div>
      </div>

      <div className="main-viewport">
        {/* TOP HEADER */}
        <header className="top-header">
            <div className="breadcrumb">
                <h2>{activeTab.toUpperCase()}</h2>
                <p>Analiza łańcucha dostaw w czasie rzeczywistym</p>
            </div>

            <div className="simulation-widget">
                <div className="sim-time">
                    <span className="label">DATA SYSTEMOWA</span>
                    <span className="val">{simulationStatus?.current_date}</span>
                </div>
                <button 
                    onClick={() => axios.post(`${API_URL}/simulation/toggle`)} 
                    className={`sim-action ${simulationStatus?.is_running ? 'stop' : 'start'}`}
                >
                    {simulationStatus?.is_running ? <X size={16}/> : <Activity size={16}/>}
                    {simulationStatus?.is_running ? 'STOP' : 'RUN'}
                </button>
            </div>
        </header>

        <div className="content-scroll">

            {/* DASHBOARD ANALITYCZNY */}
            {activeTab === 'analytics' && analyticsData && (
                <div className="view-fade">
                    <div className="kpi-grid">
                        <div className="kpi-tile gradient-blue">
                            <div className="kpi-icon"><DollarSign/></div>
                            <div className="kpi-info"><span>Wydatki Łączne</span><h3>{analyticsData.summary.total_spend.toLocaleString()} PLN</h3></div>
                        </div>
                        <div className="kpi-tile gradient-red">
                            <div className="kpi-icon"><Shield/></div>
                            <div className="kpi-info"><span>Oszczędność AI</span><h3>{analyticsData.summary.blocked_value.toLocaleString()} PLN</h3></div>
                        </div>
                        <div className="kpi-tile gradient-green">
                            <div className="kpi-icon"><Activity/></div>
                            <div className="kpi-info"><span>Efektywność JIT</span><h3>{100 - analyticsData.security.fraud_rate}%</h3></div>
                        </div>
                        <div className="kpi-tile gradient-orange">
                            <div className="kpi-icon"><Zap/></div>
                            <div className="kpi-info">
                                <span>Koszty Interwencyjne</span>
                                <h3>{analyticsData.emergency_premium_cost?.toLocaleString() || 0} PLN</h3>
                                <span style={{fontSize:'0.75rem', color:'#d97706', fontWeight:600}}>{analyticsData.emergency_count || 0} akcji ratunkowych</span>
                            </div>
                        </div>
                    </div>

                    {/* REKOMENDACJE RENEGOCJACJI */}
                    {analyticsData.ai_negotiations && analyticsData.ai_negotiations.length > 0 && (
                        <div className="card" style={{marginBottom: '25px', border: '2px solid #c084fc', background: '#faf5ff'}}>
                            <div style={{display:'flex', alignItems:'center', gap:'10px', color:'#7e22ce', marginBottom:'15px'}}>
                                <Handshake size={24} />
                                <h3 style={{margin:0}}>Sygnały Renegocjacji Kontraktów (Analiza Trendów AI - 30 dni)</h3>
                            </div>
                            <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(300px, 1fr))', gap:'20px'}}>
                                {analyticsData.ai_negotiations.map((neg, idx) => (
                                    <div key={idx} style={{background:'white', padding:'20px', borderRadius:'16px', border:'1px solid #e9d5ff', boxShadow:'0 4px 6px -1px rgba(0, 0, 0, 0.05)'}}>
                                        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'10px'}}>
                                            <strong style={{fontSize:'1.1rem', color:'#4c1d95'}}>{neg.product_name}</strong>
                                            <span style={{background:'#dcfce7', color:'#166534', padding:'4px 10px', borderRadius:'20px', fontSize:'0.8rem', fontWeight:'bold'}}>
                                                +{neg.growth_percent}% Popytu
                                            </span>
                                        </div>
                                        <p style={{fontSize:'0.9rem', color:'#6b7280', margin:'0 0 10px 0', fontStyle:'italic'}}>
                                            Wolumen za ost. 30 dni: {neg.recent_volume} szt.
                                        </p>
                                        <div style={{background:'#f3e8ff', padding:'12px', borderRadius:'8px', fontSize:'0.9rem', color:'#6b21a8', fontWeight:'500'}}>
                                            {neg.suggestion}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="chart-section">
                        <div className="main-chart card">
                            <div className="chart-header">
                                <div><h4>Strategia Doboru Dostawców</h4><p>Optymalizacja Koszt vs Ryzyko (Lead-Time)</p></div>
                                <Gavel size={20} color="#6366f1"/>
                            </div>
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={analyticsData.sourcing_stats}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9"/>
                                    <XAxis dataKey="name" fontSize={11} stroke="#64748b" axisLine={false} tickLine={false}/>
                                    <YAxis fontSize={11} stroke="#64748b" axisLine={false} tickLine={false}/>
                                    <Tooltip cursor={{fill: '#f8fafc'}} contentStyle={{borderRadius:'10px', border:'none', boxShadow:'0 10px 15px -3px rgba(0,0,0,0.1)'}}/>
                                    <Bar dataKey="value" radius={[6, 6, 0, 0]} barSize={50}>
                                        {analyticsData.sourcing_stats.map((e, i) => <Cell key={i} fill={i === 0 ? '#6366f1' : '#f59e0b'}/>)}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>

                        <div className="side-chart card">
                            <h4>Audyt Bezpieczeństwa</h4>
                            <ResponsiveContainer width="100%" height={250}>
                                <PieChart>
                                    <Pie data={[{name:'Zatwierdzone', value: analyticsData.security.approved_value}, {name:'Anomalia', value: analyticsData.security.blocked_value}]} innerRadius={60} outerRadius={85} dataKey="value" paddingAngle={5} stroke="none">
                                        <Cell fill="#10b981"/><Cell fill="#f43f5e"/>
                                    </Pie>
                                    <Tooltip/>
                                    <Legend verticalAlign="bottom" iconType="circle"/>
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    <div className="card sawtooth-card" style={{marginTop:'25px'}}>
                        <div className="chart-header">
                            <div><h4>Cykl Magazynowy (Wykres Piłokształtny)</h4><p>Wizualizacja dostaw JIT i zużycia bieżącego</p></div>
                            <TrendingUp color="#6366f1"/>
                        </div>
                        <ResponsiveContainer width="100%" height={300}>
                            <AreaChart data={history}>
                                <defs>
                                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2}/>
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9"/>
                                <XAxis dataKey="shortDate" fontSize={10} stroke="#94a3b8" axisLine={false}/>
                                <YAxis fontSize={10} stroke="#94a3b8" axisLine={false}/>
                                <Tooltip/>
                                <Area type="monotone" dataKey="total_inventory_value" stroke="#6366f1" strokeWidth={3} fill="url(#colorValue)" animationDuration={1500}/>
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>

                    {/* DZIENNIK INTERWENCJI STRATEGICZNYCH AI */}
                    <div className="card interventions-card" style={{marginTop:'25px', overflow:'hidden', padding:'0'}}>
                        <div style={{padding:'20px', background:'#f8fafc', borderBottom:'1px solid #e2e8f0', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                            <div>
                                <h4 style={{margin:0, display:'flex', alignItems:'center', gap:'10px'}}>
                                    <ShieldCheck size={20} color="#10b981"/> 
                                    Dziennik Interwencji Strategicznych AI
                                </h4>
                                <p style={{margin:'4px 0 0 0', fontSize:'0.85rem', color:'#64748b'}}>Rejestr autonomicznych decyzji ratunkowych i blokad oszustw. Kliknij wiersz, aby zobaczyć wyjaśnienie AI.</p>
                            </div>
                        </div>
                        <div style={{overflowX: 'auto'}}>
                            <table className="premium-table interactive-table" style={{margin:0}}>
                                <thead>
                                    <tr>
                                        <th>DATA SYSTEMOWA</th>
                                        <th>ID ZDARZENIA</th>
                                        <th>TYP REAKCJI</th>
                                        <th>CEL (PRODUKT)</th>
                                        <th style={{textAlign: 'right'}}>SKUTEK</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {analyticsData.ai_interventions && analyticsData.ai_interventions.length > 0 ? (
                                        analyticsData.ai_interventions.map((inv, i) => (
                                            <tr key={i} className="row-hover" onClick={() => setSelectedIntervention(inv)}>
                                                <td style={{color:'#64748b', fontSize:'0.85rem'}}>{inv.date}</td>
                                                <td style={{fontFamily:'monospace', fontWeight:'bold'}}>{inv.id}</td>
                                                <td>
                                                    <span className={`status-pill-big ${inv.color === 'red' ? 'critical' : 'safe'}`} style={{background: inv.color === 'red' ? '#fee2e2' : '#dbeafe', color: inv.color === 'red' ? '#be123c' : '#1d4ed8', cursor:'pointer'}}>
                                                        {inv.type}
                                                    </span>
                                                </td>
                                                <td style={{fontWeight:600}}>{inv.product}</td>
                                                <td style={{textAlign: 'right', fontWeight:700, color: inv.color === 'red' ? '#dc2626' : '#059669'}}>
                                                    {inv.impact}
                                                </td>
                                            </tr>
                                        ))
                                    ) : (
                                        <tr><td colSpan="5" style={{textAlign:'center', color:'#94a3b8', padding:'30px'}}>Brak krytycznych interwencji w obecnej sesji.</td></tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>

                </div>
            )}

            {/* MAGAZYN MRP */}
            {activeTab === 'forecast' && (
                <div className="card table-view view-fade" style={{padding:0, overflow:'hidden'}}>
                    <div className="table-header-premium">
                        <div className="title-group">
                            <h3>Magazyn MRP (Just-in-Time)</h3>
                            <p>Symulacja cykli produkcyjnych i zapasów bezpieczeństwa</p>
                        </div>
                    </div>
                    <table className="premium-table">
                        <thead>
                            <tr>
                                <th>PRODUKT</th>
                                <th>ZAPAS</th>
                                <th>W DRODZE</th>
                                <th>EST. DOSTAWA</th>
                                <th>DNI ZAPASU</th>
                                <th>REKOMENDACJA AI</th>
                                <th>STATUS</th>
                                <th>AKCJA</th>
                            </tr>
                        </thead>
                        <tbody>
                            {predictions.map(p => (
                                <tr key={p.id} className="row-hover">
                                    <td style={{fontWeight:700}}>{p.product_name}</td>
                                    <td>{p.current_stock}</td>
                                    <td style={{color:'#6366f1', fontWeight:800}}>{p.incoming_stock > 0 ? `+${p.incoming_stock}` : '-'}</td>
                                    <td style={{fontSize:'0.85rem', color:'#64748b'}}>
                                        {p.next_delivery_date ? (
                                            <div style={{display:'flex', alignItems:'center', gap:'6px', color:'#4f46e5', fontWeight:600}}>
                                                <Truck size={14}/> {p.next_delivery_date}
                                            </div>
                                        ) : '---'}
                                    </td>
                                    <td className="days-td"><div className={`days-badge ${p.days_left < 4 ? 'critical' : ''}`}>{p.days_left} d</div></td>
                                    <td className="advice-td" style={{fontSize:'0.75rem', fontStyle:'italic', color:'#6366f1'}}>{p.ai_supplier_advice}</td>
                                    <td><span className={`status-pill-big ${p.status}`}>{p.status.toUpperCase()}</span></td>
                                    <td>{p.restock_recommended && <button onClick={() => handleOrder(p)} className="action-btn-small">Zamów</button>}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* MONITORING LOGISTYKI */}
            {activeTab === 'orders' && (
                <div className="card table-view view-fade" style={{padding:0, overflow:'hidden'}}>
                    <div className="table-header-premium">
                        <div className="title-group"><h3>Monitorowanie Zamówień</h3><p>Status dostaw i strategii sourcingowych</p></div>
                        <button onClick={fetchOrders} className="icon-btn"><RefreshCw size={18}/></button>
                    </div>
                    <table className="premium-table">
                        <thead>
                            <tr><th>ID DOKUMENTU</th><th>STRATEGIA AI</th><th>PRODUKT</th><th>WARTOŚĆ</th><th>ESTYMACJA DOSTAWY</th><th>STATUS</th></tr>
                        </thead>
                        <tbody>
                            {orders.map(o => (
                                <tr key={o.id} onClick={() => setSelectedOrder(o)} className="row-hover interactive-table">
                                    <td className="id-cell">{o.id}</td>
                                    <td><span className={`strat-tag ${o.order_type === 'KOSZT' ? 'cost' : 'risk'}`}>{o.order_type || 'KOSZT'}</span></td>
                                    <td className="p-name-cell">{o.product?.name}</td>
                                    <td className="val-cell">{o.total_price.toFixed(2)} PLN</td>
                                    <td>{o.estimated_delivery?.split('T')[0]}</td>
                                    <td><span className={`status-pill-big ${o.status}`}>{o.status === 'ordered' ? 'W DRODZE' : o.status.toUpperCase()}</span></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* SMART WALLET */}
            {activeTab === 'contracts' && analyticsData && (
                <div className="view-fade">
                    <div className="wallet-card card">
                        <div className="wallet-main">
                            <div className="wallet-icon"><Wallet size={40} color="#fff"/></div>
                            <div className="wallet-balance">
                                <span>DOSTĘPNY BUDŻET OPERACYJNY</span>
                                <h1>{analyticsData.wallet.available_funds.toLocaleString()} PLN</h1>
                            </div>
                        </div>
                        <div className="wallet-progress">
                            <div className="progress-info">
                                <span>Wykorzystanie limitu: {analyticsData.wallet.spent_percent}%</span>
                                <span>Limit: {analyticsData.wallet.total_budget.toLocaleString()} PLN</span>
                            </div>
                            <div className="progress-track"><div className="progress-fill" style={{width: `${analyticsData.wallet.spent_percent}%`}}></div></div>
                        </div>
                    </div>
                    <div className="card ocr-section" style={{marginTop:'30px', textAlign:'center', padding:'60px', border:'2px dashed #e2e8f0'}}>
                        <Upload size={40} color="#6366f1" style={{margin:'0 auto 20px'}}/>
                        <h3>Import Dokumentów AI</h3>
                        <p style={{color:'#64748b'}}>Przeciągnij plik PDF kontraktu, aby automatycznie zaktualizować bazy cennikowe.</p>
                    </div>
                </div>
            )}

            {/* WHAT-IF RYKO */}
            {activeTab === 'scenarios' && (
                <div className="view-fade">
                    <div className="control-panel card">
                        <div className="slider-box">
                            <label>Opóźnienie Logistyczne: <strong>{delayDays} dni</strong></label>
                            <input type="range" min="0" max="14" value={delayDays} onChange={e=>setDelayDays(e.target.value)} />
                        </div>
                        <div className="slider-box">
                            <label>Szok Popytowy: <strong>+{demandSpike}%</strong></label>
                            <input type="range" min="0" max="100" value={demandSpike} onChange={e=>setDemandSpike(e.target.value)} />
                        </div>
                    </div>
                    <div className="card scenario-chart" style={{marginTop:'25px'}}>
                        <h4>Symulacja Wpływu na Zapas (Model Monte Carlo Lite)</h4>
                        <ResponsiveContainer width="100%" height={450}>
                            <AreaChart data={scenarios}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9"/>
                                <XAxis dataKey="day" fontSize={11}/><YAxis fontSize={11}/><Tooltip/>
                                <Area type="monotone" dataKey="baseline" stroke="#94a3b8" fill="#f8fafc" strokeDasharray="5 5" name="Stan Normalny"/>
                                <Area type="monotone" dataKey="stock" stroke="#a855f7" fill="#f3e8ff" name="Prognoza Scenariusza" strokeWidth={3}/>
                                <Legend verticalAlign="top" align="right"/>
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            )}

            {/* MARKETPLACE AI */}
            {activeTab === 'market' && (
                <div className="market-view view-fade">
                    <div className="market-search card">
                        <Search size={20} color="#94a3b8"/>
                        <input type="text" placeholder="Szukaj produktów (Semantic AI Search)..." onChange={e => fetchProducts(e.target.value)} />
                    </div>
                    <div className="product-grid">
                        {products.map(p => (
                            <div key={p.id} className="product-tile">
                                <div className="tile-head"><h4>{p.name}</h4><span className="cat-tag">{p.category}</span></div>
                                <div className="tile-body">
                                    <div className="info-line"><span>Cena katalogowa</span><strong>{p.unit_cost.toFixed(2)} PLN</strong></div>
                                    <div className="info-line"><span>Stan magazynu</span><strong style={{color: p.current_stock < 10 ? '#ef4444' : '#10b981'}}>{p.current_stock} {p.unit}</strong></div>
                                </div>
                                <button onClick={() => handleOrder(p)} className="buy-btn">Złóż Zamówienie</button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

        </div>
      </div>

      {/* MODAL SZCZEGÓŁÓW ZAMÓWIENIA */}
      {selectedOrder && (
          <div className="modal-backdrop">
              <div className="modal-container animate-scale">
                  <div className="modal-top">
                    <h3>DOKUMENT: {selectedOrder.id}</h3>
                    <X className="close-icon" onClick={() => setSelectedOrder(null)}/>
                  </div>
                  <div className="modal-content-area">
                      <div className="proforma-box">
                          <div className="box-header">SYMULACJA FAKTURY PROFORMA</div>
                          <div className="box-line"><span>Produkt:</span> <strong>{selectedOrder.product?.name}</strong></div>
                          <div className="box-line"><span>Wartość Netto:</span> <span>{calculateInvoice(selectedOrder).net.toFixed(2)} PLN</span></div>
                          <div className="box-total"><span>BRUTTO:</span> <span>{calculateInvoice(selectedOrder).gross.toFixed(2)} PLN</span></div>
                      </div>
                      <div className="compliance-msg"><ShieldCheck size={18}/> Weryfikacja AI: Zgodność z budżetem Smart Wallet.</div>
                  </div>
              </div>
          </div>
      )}

      {/* MODAL EXPLAINABLE AI (XAI) DLA INTERWENCJI */}
      {selectedIntervention && (
          <div className="modal-backdrop">
              <div className="modal-container animate-scale xai-modal">
                  <div className={`modal-top xai-top ${selectedIntervention.color === 'red' ? 'xai-red' : 'xai-blue'}`}>
                    <div style={{display:'flex', alignItems:'center', gap:'12px'}}>
                        <BrainCircuit size={28} />
                        <div>
                            <h3 style={{margin:0, fontSize:'1.2rem'}}>Wyjaśnienie Modelu AI (XAI)</h3>
                            <span style={{fontSize:'0.8rem', opacity:0.8}}>ID Zdarzenia: {selectedIntervention.id}</span>
                        </div>
                    </div>
                    <X className="close-icon" style={{color:'white'}} onClick={() => setSelectedIntervention(null)}/>
                  </div>
                  <div className="modal-content-area" style={{padding:'30px'}}>
                      <div className="xai-detail-row">
                          <span className="xai-label">Produkt poddany ocenie:</span>
                          <strong className="xai-value">{selectedIntervention.product}</strong>
                      </div>
                      <div className="xai-detail-row">
                          <span className="xai-label">Typ podjętej akcji:</span>
                          <strong className="xai-value">{selectedIntervention.type}</strong>
                      </div>
                      <div className="xai-detail-row">
                          <span className="xai-label">Skutek finansowy/operacyjny:</span>
                          <strong className="xai-value" style={{color: selectedIntervention.color === 'red' ? '#dc2626' : '#059669'}}>
                              {selectedIntervention.impact}
                          </strong>
                      </div>
                      
                      <div className="xai-reason-box">
                          <div className="xai-reason-header">
                              <Terminal size={16}/> Logika decyzyjna algorytmu:
                          </div>
                          <div className="xai-reason-text">
                              {selectedIntervention.reason || "Brak szczegółowego uzasadnienia dla tego zdarzenia."}
                          </div>
                      </div>
                  </div>
              </div>
          </div>
      )}

      {/* CHAT AI */}
      <div className={`chat-bubble-widget ${isChatOpen ? 'expanded' : ''}`}>
          {isChatOpen ? (
              <div className="chat-window card">
                  <div className="chat-header-bar"><span>Asystent ProcureBot AI</span><X size={18} onClick={() => setIsChatOpen(false)} style={{cursor:'pointer'}}/></div>
                  <div className="chat-content">
                      {chatMessages.map((m, i) => (<div key={i} className={`msg-row ${m.from}`}><div className="bubble">{m.text}</div></div>))}
                      <div ref={chatEndRef}/>
                  </div>
                  <form onSubmit={handleSendMessage} className="chat-input-row">
                      <input value={chatInput} onChange={e => setChatInput(e.target.value)} placeholder="Zadaj pytanie..."/>
                      <button type="submit"><Send size={16}/></button>
                  </form>
              </div>
          ) : (
              <button className="chat-trigger" onClick={() => setIsChatOpen(true)}>
                  <MessageSquare size={28}/>
                  <div className="pulse"></div>
              </button>
          )}
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap');
        
        :root { --primary: #6366f1; --primary-dark: #4f46e5; --bg: #f8fafc; --sidebar: #0f172a; --card: #ffffff; --text: #1e293b; --text-muted: #64748b; }

        .app-layout { display: flex; height: 100vh; background: var(--bg); font-family: 'Inter', sans-serif; color: var(--text); overflow: hidden; }
        .sidebar { width: 280px; background: var(--sidebar); color: white; padding: 30px; display: flex; flex-direction: column; z-index:10; }
        .logo-area { display: flex; align-items: center; gap: 15px; margin-bottom: 50px; }
        .logo-box { background: var(--primary); padding: 10px; border-radius: 12px; }
        .logo-title { font-weight: 900; font-size: 1.3rem; letter-spacing: -0.5px; display: block; }
        .logo-tag { font-size: 0.65rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; }
        .nav-group-label { font-size: 0.65rem; color: #475569; font-weight: 800; letter-spacing: 1.5px; margin-bottom: 12px; }
        .nav-item { width: 100%; display: flex; align-items: center; gap: 14px; padding: 14px; background: transparent; border: none; color: #94a3b8; border-radius: 12px; cursor: pointer; font-size: 0.95rem; margin-bottom: 5px; text-align: left; transition: 0.3s; }
        .nav-item:hover, .nav-item.active { background: #1e293b; color: white; }
        .nav-item.active { background: var(--primary) !important; box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.3); }
        .main-viewport { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .top-header { padding: 30px 40px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; background:white; z-index:5; }
        .simulation-widget { display: flex; align-items: center; gap: 25px; background: white; padding: 12px 25px; border-radius: 60px; border: 1px solid #e2e8f0; }
        .sim-time .val { font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--primary); }
        .sim-action { border: none; padding: 10px 20px; border-radius: 30px; cursor: pointer; display: flex; align-items: center; gap: 8px; font-weight: 800; transition:0.2s;}
        .sim-action:hover { transform: scale(1.05); }
        .sim-action.start { background: #dcfce7; color: #16a34a; }
        .sim-action.stop { background: #fee2e2; color: #dc2626; }
        .content-scroll { flex: 1; overflow-y: auto; padding: 40px; }
        .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 25px; margin-bottom: 35px; }
        .kpi-tile { background: white; padding: 30px; border-radius: 24px; border: 1px solid #e2e8f0; display: flex; align-items: center; gap: 20px; }
        .kpi-icon { width: 55px; height: 55px; border-radius: 16px; display: flex; align-items: center; justify-content: center; color: white; }
        .gradient-blue .kpi-icon { background: linear-gradient(135deg, #6366f1, #4f46e5); }
        .gradient-red .kpi-icon { background: linear-gradient(135deg, #f43f5e, #e11d48); }
        .gradient-green .kpi-icon { background: linear-gradient(135deg, #10b981, #059669); }
        .gradient-orange .kpi-icon { background: linear-gradient(135deg, #f59e0b, #d97706); }
        .card { background: white; border-radius: 24px; border: 1px solid #e2e8f0; padding: 30px; }
        .premium-table { width: 100%; border-collapse: collapse; }
        .premium-table th { text-align: left; padding: 20px; background: #f8fafc; color: var(--text-muted); font-size: 0.75rem; font-weight: 800; text-transform: uppercase; }
        .premium-table td { padding: 20px; border-bottom: 1px solid #f1f5f9; font-size: 0.95rem; }
        .interactive-table tr { cursor: pointer; transition: background 0.2s; }
        .interactive-table tr:hover { background-color: #f8fafc; }
        .status-pill-big { padding: 6px 14px; border-radius: 30px; font-size: 0.7rem; font-weight: 900; display: inline-block;}
        .status-pill-big.safe { background: #dcfce7; color: #15803d; }
        .status-pill-big.warning { background: #fef3c7; color: #b45309; }
        .status-pill-big.critical { background: #fee2e2; color: #be123c; }
        .days-badge { background: #f1f5f9; padding: 6px 12px; border-radius: 8px; font-weight: 800; width: fit-content; }
        .days-badge.critical { background: #fee2e2; color: #dc2626; }
        .wallet-card { background: var(--sidebar); color: white; }
        .progress-track { height: 12px; background: #1e293b; border-radius: 10px; margin-top: 15px; }
        .progress-fill { height: 100%; background: var(--primary); border-radius: 10px; transition: 1s; }
        .action-btn-small { padding: 8px 16px; background: var(--sidebar); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 700; transition:0.2s; }
        .action-btn-small:hover { background: var(--primary); }
        .product-tile { background: white; padding: 25px; border-radius: 24px; border: 1px solid #e2e8f0; }
        .buy-btn { width: 100%; padding: 12px; border-radius: 12px; border: none; background: var(--sidebar); color: white; font-weight: 700; cursor: pointer; margin-top: 15px; transition:0.2s;}
        .buy-btn:hover { background: var(--primary); }
        
        /* Modal Styles */
        .modal-backdrop { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 9999; }
        .modal-container { background: white; width: 500px; border-radius: 24px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); }
        .modal-top { background: #f8fafc; padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; }
        .modal-top h3 { margin: 0; font-size: 1.1rem; color: #1e293b; }
        .close-icon { cursor: pointer; color: #64748b; transition: 0.2s; }
        .close-icon:hover { color: #0f172a; transform: rotate(90deg); }
        .modal-content-area { padding: 30px; }
        .proforma-box { border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        .box-header { font-size: 0.75rem; font-weight: 800; color: #94a3b8; margin-bottom: 15px; text-transform: uppercase; }
        .box-line { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 0.95rem; }
        .box-total { display: flex; justify-content: space-between; margin-top: 15px; padding-top: 15px; border-top: 1px dashed #e2e8f0; font-weight: 800; font-size: 1.1rem; color: var(--primary); }
        .compliance-msg { display: flex; align-items: center; gap: 10px; background: #f0fdf4; color: #166534; padding: 15px; border-radius: 12px; font-weight: 600; font-size: 0.9rem; }
        
        /* XAI Modal Specific Styles */
        .xai-modal { width: 600px; }
        .xai-top { color: white; border-bottom: none; }
        .xai-top h3 { color: white; }
        .xai-blue { background: linear-gradient(135deg, #3b82f6, #1d4ed8); }
        .xai-red { background: linear-gradient(135deg, #ef4444, #be123c); }
        .xai-detail-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #f1f5f9; }
        .xai-label { color: #64748b; font-size: 0.9rem; }
        .xai-value { font-size: 1rem; color: #0f172a; }
        .xai-reason-box { margin-top: 25px; background: #1e293b; border-radius: 12px; overflow: hidden; }
        .xai-reason-header { background: #0f172a; color: #94a3b8; padding: 12px 20px; font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; display: flex; align-items: center; gap: 10px; }
        .xai-reason-text { padding: 20px; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; line-height: 1.6; }

        .chat-bubble-widget { position: fixed; bottom: 30px; right: 30px; z-index: 1000; }
        .chat-trigger { width: 65px; height: 65px; border-radius: 50%; background: var(--primary); color: white; border: none; cursor: pointer; box-shadow: 0 10px 25px rgba(0,0,0,0.1); position: relative; }
        .chat-window { width: 380px; height: 550px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
        .chat-header-bar { background: var(--primary); color: white; padding: 15px 20px; font-weight: 800; display: flex; justify-content: space-between; }
        .bubble { padding: 12px 16px; border-radius: 18px; font-size: 0.9rem; max-width: 85%; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .msg-row.bot .bubble { background: white; border: 1px solid #e2e8f0; align-self: flex-start; }
        .msg-row.user .bubble { background: var(--primary); color: white; align-self: flex-end; }
        .chat-content { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        .chat-input-row { padding: 15px; border-top: 1px solid #e2e8f0; display: flex; gap: 10px; }
        .chat-input-row input { flex: 1; border: 1px solid #e2e8f0; border-radius: 20px; padding: 10px 15px; outline:none;}
        .chat-input-row input:focus { border-color: var(--primary); }
        .chat-input-row button { background: var(--primary); color: white; border: none; width: 40px; height: 40px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        
        .animate-scale { animation: scaleIn 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
        @keyframes scaleIn { from { transform: scale(0.95); opacity: 0; } to { transform: scale(1); opacity: 1; } }
      `}</style>

    </div>
  )
}

export default App