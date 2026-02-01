import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import { 
    ShoppingCart, 
    Package, 
    RefreshCw, 
    AlertTriangle, 
    Search, 
    FileText, 
    Upload, 
    CheckCircle, 
    Clock, 
    CheckSquare, 
    ShieldCheck,
    Boxes, 
    Filter, 
    BarChart3, 
    TrendingUp, 
    CalendarRange, 
    UserCircle, 
    Download, 
    XCircle, 
    Check, 
    Info, 
    FileSpreadsheet, 
    Building2, 
    X, 
    Wallet, 
    Banknote, 
    Repeat, 
    MessageSquare, 
    Send, 
    Settings, 
    Activity,
    Terminal, // Zachowany import
    Shield,
    DollarSign
} from 'lucide-react'
import { 
    AreaChart, 
    Area, 
    XAxis, 
    YAxis, 
    CartesianGrid, 
    Tooltip, 
    ResponsiveContainer,
    BarChart, 
    Bar, 
    Legend, 
    Line, 
    ComposedChart, 
    Cell 
} from 'recharts';

function App() {
  // --- STANY APLIKACJI ---
  const [activeTab, setActiveTab] = useState('market')
  const [userRole, setUserRole] = useState('employee')
  
  // Dane biznesowe
  const [products, setProducts] = useState([])
  const [orders, setOrders] = useState([])
  const [history, setHistory] = useState([]) 
  const [predictions, setPredictions] = useState([]) 
  
  // NOWE DANE ANALITYCZNE (Zamiast starego finance)
  const [analyticsData, setAnalyticsData] = useState(null)
  
  const [scenarios, setScenarios] = useState([]) 
  // Stan symulacji
  const [simulationStatus, setSimulationStatus] = useState({ 
      date: "Loading...", 
      is_running: false, 
      events: [] 
  })
  
  // Parametry symulacji What-If
  const [delayDays, setDelayDays] = useState(0)
  const [demandSpike, setDemandSpike] = useState(0)

  // Chatbot AI
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [chatInput, setChatInput] = useState("")
  const [chatMessages, setChatMessages] = useState([
      { from: 'bot', text: 'Witaj! Jestem asystentem zakupowym. Jak mogę pomóc?' }
  ])
  const chatEndRef = useRef(null)

  // UI & Filtry
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [showLowStockOnly, setShowLowStockOnly] = useState(false)
  
  // Smart Wallet (Kontrakty)
  const [selectedFile, setSelectedFile] = useState(null)
  const [contractDraft, setContractDraft] = useState(null)
  const [uploading, setUploading] = useState(false)

  // Modal Szczegółów Zamówienia
  const [selectedOrder, setSelectedOrder] = useState(null)

  const API_URL = 'http://127.0.0.1:8000'

  // --- POBIERANIE DANYCH (Cykl Życia) ---
  useEffect(() => {
    fetchSimulationStatus()
    fetchProducts()
    
    const interval = setInterval(() => {
        fetchSimulationStatus()
        
        // Inteligentne odświeżanie w zależności od aktywnej zakładki
        if (activeTab === 'orders') {
            fetchOrders()
        }
        if (activeTab === 'inventory') {
            fetchProducts()
        }
        if (activeTab === 'analytics') { 
            fetchAnalyticsDashboard() // NOWA FUNKCJA
            fetchHistory()
        }
        if (activeTab === 'forecast') { 
            fetchPredictions()
            if (products.length === 0) fetchProducts()
        }
    }, 2000) // Zwiększyłem interwał do 2s dla płynności
    
    return () => clearInterval(interval)
  }, [activeTab])

  // Odświeżanie scenariusza What-If
  useEffect(() => {
      if (activeTab === 'scenarios') {
          fetchScenarios()
      }
  }, [delayDays, demandSpike, activeTab])

  // Auto-scroll czatu
  useEffect(() => {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chatMessages])

  // --- FUNKCJE API ---

  const fetchProducts = async (query = "") => {
    if (!['inventory', 'orders', 'analytics', 'forecast', 'scenarios'].includes(activeTab)) {
        setLoading(true)
    }
    try {
      const endpoint = query 
        ? `${API_URL}/products?search=${query}&limit=100`
        : `${API_URL}/products?limit=100`
      const response = await axios.get(endpoint)
      setProducts(response.data)
    } catch (error) {
      console.error("Błąd produktów:", error)
    } finally {
      setLoading(false)
    }
  }

  const fetchOrders = async () => {
      try {
          const response = await axios.get(`${API_URL}/orders?limit=50`)
          setOrders(response.data)
      } catch (error) { console.error(error) }
  }

  const fetchHistory = async () => {
      try {
          const response = await axios.get(`${API_URL}/analytics/history`)
          const formattedData = response.data.map(item => ({
              ...item,
              shortDate: new Date(item.date).toLocaleDateString(undefined, {month:'numeric', day:'numeric'})
          }))
          setHistory(formattedData)
      } catch (error) { console.error(error) }
  }

  const fetchPredictions = async () => {
      try {
          const response = await axios.get(`${API_URL}/analytics/predictions?limit=50`)
          setPredictions(response.data)
      } catch (error) { console.error(error) }
  }

  // NOWA FUNKCJA DO DASHBOARDU
  const fetchAnalyticsDashboard = async () => {
      try {
          const response = await axios.get(`${API_URL}/analytics/dashboard`)
          setAnalyticsData(response.data)
      } catch (error) { console.error("Błąd dashboardu:", error) }
  }

  const fetchScenarios = async () => {
      try {
          const response = await axios.get(`${API_URL}/analytics/what-if?delay_days=${delayDays}&demand_spike=${demandSpike}`)
          setScenarios(response.data)
      } catch (error) { console.error(error) }
  }

  const fetchSimulationStatus = async () => {
    try {
      const response = await axios.get(`${API_URL}/simulation/status`)
      setSimulationStatus(response.data)
    } catch (error) { console.error(error) }
  }

  // --- OBSŁUGA CZATU ---

  const handleSendMessage = async (e) => {
      e.preventDefault()
      if (!chatInput.trim()) return

      const userMsg = chatInput
      setChatMessages(prev => [...prev, { from: 'user', text: userMsg }])
      setChatInput("")
      
      try {
          const response = await axios.post(`${API_URL}/assistant/chat`, { message: userMsg })
          setChatMessages(prev => [...prev, { from: 'bot', text: response.data.text }])
          
          if (response.data.action === 'download_report') {
              downloadReport()
          }
      } catch (error) {
          setChatMessages(prev => [...prev, { from: 'bot', text: "Błąd połączenia z serwerem AI." }])
      }
  }

  // --- AKCJE UŻYTKOWNIKA ---

  const toggleSimulation = async () => {
    try {
        const response = await axios.post(`${API_URL}/simulation/toggle`)
        setSimulationStatus(prev => ({
            ...prev,
            is_running: response.data.status === 'running'
        }))
    } catch (error) {
        alert("Błąd połączenia z backendem: " + error.message)
    }
  }
  
  const handleOrder = async (item) => {
    let pid = item.id
    let name = item.name || item.product_name

    if (!pid) {
        const p = products.find(x => x.name === name)
        if (p) pid = p.id
        else return alert("Błąd: Nie znaleziono ID produktu. Spróbuj odświeżyć.")
    }

    const qty = prompt(`Podaj ilość do zamówienia dla: ${name}`, "20")
    if (!qty) return

    try {
      await axios.post(`${API_URL}/orders`, {
        product_id: pid,
        supplier_id: 1, // Mock supplier
        quantity: parseFloat(qty),
        order_type: "standard"
      })
      alert("✅ Zamówienie wysłane!")
      fetchOrders()
    } catch (error) {
      alert("Błąd zamówienia: " + (error.response?.data?.detail || error.message))
    }
  }

  const handleFindAlternatives = async (product) => {
    const confirmSearch = confirm(`Czy chcesz znaleźć zamienniki AI dla produktu: ${product.name}?`)
    if (!confirmSearch) return

    try {
        const response = await axios.get(`${API_URL}/products/${product.id}/alternatives`)
        const alts = response.data
        
        if (alts.length === 0) {
            alert("AI: Nie znaleziono wystarczająco podobnych zamienników w tej kategorii.")
        } else {
            let message = `🧠 AI SUGERUJE ZAMIENNIKI:\n\n`
            alts.forEach(alt => {
                message += `🔹 ${alt.name} (Stan: ${alt.current_stock} ${alt.unit})\n`
            })
            alert(message)
        }
    } catch (error) {
        alert("Błąd AI: " + error.message)
    }
  }

  const handleApprove = async (orderId) => {
      try { 
          await axios.put(`${API_URL}/orders/${orderId}/approve`)
          fetchOrders()
          setSelectedOrder(null)
      } catch(e) { alert(e.message) }
  }

  const handleReject = async (orderId) => {
      try { 
          await axios.put(`${API_URL}/orders/${orderId}/reject`)
          fetchOrders()
          setSelectedOrder(null) 
      } catch(e) { alert(e.message) }
  }

  const downloadReport = () => {
      window.open(`${API_URL}/analytics/report/pdf`, '_blank')
  }

  const downloadOrderPDF = (id) => {
      window.open(`${API_URL}/orders/${id}/pdf`, '_blank')
  }

  const handleFileChange = (e) => {
      setSelectedFile(e.target.files[0])
      setContractDraft(null)
  }

  const analyzeContract = async () => {
      if (!selectedFile) return alert("Wybierz plik!")
      setUploading(true)
      const formData = new FormData()
      formData.append("file", selectedFile)
      
      try {
          const response = await axios.post(`${API_URL}/contracts/upload`, formData, {
              headers: { 'Content-Type': 'multipart/form-data' }
          })
          setContractDraft(response.data)
      } catch (error) {
          alert(error.message)
      } finally {
          setUploading(false)
      }
  }

  const confirmContract = async () => {
      try {
          await axios.post(`${API_URL}/contracts/confirm`, contractDraft)
          alert("✅ Kontrakt zatwierdzony i dodany do bazy Compliance!")
          setContractDraft(null)
          setSelectedFile(null)
      } catch (error) {
          alert(error.message)
      }
  }

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    fetchProducts(searchQuery)
  }

  const inventoryProducts = showLowStockOnly 
    ? products.filter(p => p.current_stock <= p.min_stock_level)
    : products

  const calculateInvoice = (order) => {
      const net = order.total_price / 1.23
      const vat = order.total_price - net
      return { net, vat, gross: order.total_price }
  }

  // ==========================================
  // RENDEROWANIE WIDOKU (JSX)
  // ==========================================
  return (
    <div className="app-layout">
      
      {/* --- SIDEBAR --- */}
      <div className="sidebar">
        <div className="logo-section">
            <Package size={28} color="#4f46e5" />
            <div>
                <div style={{fontWeight:'800', fontSize:'1.1rem', letterSpacing:'-0.5px'}}>Procurement Pro</div>
                <div style={{fontSize:'0.7rem', color:'#64748b', fontWeight:'600'}}>AI ENTERPRISE</div>
            </div>
        </div>

        <div style={{flex: 1}}>
            <p style={{fontSize:'0.75rem', fontWeight:'700', color:'#94a3b8', paddingLeft:'16px', marginBottom:'8px'}}>MODUŁY</p>
            <button className={`nav-btn ${activeTab === 'market' ? 'active' : ''}`} onClick={() => setActiveTab('market')}>
                <Search size={20}/> Marketplace AI
            </button>
            <button className={`nav-btn ${activeTab === 'inventory' ? 'active' : ''}`} onClick={() => setActiveTab('inventory')}>
                <Boxes size={20}/> Magazyn
            </button>
            <button className={`nav-btn ${activeTab === 'forecast' ? 'active' : ''}`} onClick={() => {setActiveTab('forecast'); fetchPredictions();}}>
                <CalendarRange size={20}/> Prognoza MRP
            </button>
            <button className={`nav-btn ${activeTab === 'contracts' ? 'active' : ''}`} onClick={() => setActiveTab('contracts')}>
                <FileText size={20}/> Smart Wallet
            </button>
            <button className={`nav-btn ${activeTab === 'orders' ? 'active' : ''}`} onClick={() => {setActiveTab('orders'); fetchOrders();}}>
                <Clock size={20}/> Centrum Operacyjne
            </button>
            <button className={`nav-btn ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => {setActiveTab('analytics'); fetchAnalyticsDashboard(); fetchHistory();}}>
                <BarChart3 size={20}/> Raporty & BI
            </button>
            <button className={`nav-btn ${activeTab === 'scenarios' ? 'active' : ''}`} onClick={() => setActiveTab('scenarios')} style={{color:'#7c3aed'}}>
                <Activity size={20}/> Symulacje (Beta)
            </button>
        </div>

        <div style={{borderTop:'1px solid #e2e8f0', paddingTop:'20px'}}>
            <div style={{display:'flex', alignItems:'center', gap:'10px', marginBottom:'15px'}}>
                <div style={{width:'36px', height:'36px', borderRadius:'50%', background:'#e0e7ff', display:'flex', alignItems:'center', justifyContent:'center'}}>
                    <UserCircle size={20} color="#4f46e5"/>
                </div>
                <div>
                    <div style={{fontSize:'0.85rem', fontWeight:'600'}}>
                        {userRole === 'manager' ? 'Administrator' : 'Jan Kowalski'}
                    </div>
                    <select 
                        value={userRole} 
                        onChange={(e) => setUserRole(e.target.value)}
                        style={{fontSize:'0.75rem', border:'none', padding:'0', color:'#64748b', background:'transparent', cursor:'pointer'}}
                    >
                        <option value="employee">Pracownik</option>
                        <option value="manager">Manager</option>
                    </select>
                </div>
            </div>
        </div>
      </div>

      {/* --- CONTENT --- */}
      <div className="main-content">
        
        {/* Header */}
        <div className="header-bar">
            <div>
                <h2 style={{margin:0}}>
                    {activeTab === 'market' && 'Marketplace'}
                    {activeTab === 'inventory' && 'Stany Magazynowe'}
                    {activeTab === 'forecast' && 'Planowanie Zapotrzebowania (AI)'}
                    {activeTab === 'contracts' && 'Cyfrowe Umowy'}
                    {activeTab === 'orders' && 'Centrum Operacyjne'}
                    {activeTab === 'analytics' && 'Centrum Analityczne AI'}
                    {activeTab === 'scenarios' && 'Symulacje Strategiczne (What-If)'}
                </h2>
                <p style={{margin:'4px 0 0 0', color:'#64748b', fontSize:'0.9rem'}}>Panel zarządzania procesami zakupowymi</p>
            </div>

            <div className="card" style={{padding:'8px 16px', display:'flex', alignItems:'center', gap:'20px', borderRadius:'30px', border:'1px solid #e2e8f0', boxShadow:'none'}}>
                <div style={{textAlign:'right'}}>
                    <div style={{fontSize:'0.7rem', fontWeight:'700', color:'#94a3b8', letterSpacing:'0.5px'}}>DATA SYSTEMOWA</div>
                    <div style={{fontFamily:'monospace', fontWeight:'600', fontSize:'1rem'}}>
                        {simulationStatus?.current_date || '...'}
                    </div>
                </div>
                <button 
                    onClick={toggleSimulation}
                    style={{
                        background: simulationStatus?.is_running ? '#fee2e2' : '#dcfce7',
                        color: simulationStatus?.is_running ? '#dc2626' : '#16a34a',
                        border:'none', borderRadius:'50%', width:'40px', height:'40px', display:'flex', alignItems:'center', justifyContent:'center', cursor:'pointer'
                    }}
                >
                    {simulationStatus?.is_running ? 
                        <div style={{width:'12px', height:'12px', background:'currentColor', borderRadius:'2px'}}/> : 
                        <div style={{width:0, height:0, borderTop:'6px solid transparent', borderBottom:'6px solid transparent', borderLeft:'10px solid currentColor', marginLeft:'3px'}}/>
                    }
                </button>
            </div>
        </div>

        {/* --- SCENARIOS --- */}
        {activeTab === 'scenarios' && (
            <div>
                <div style={{display:'flex', gap:'20px', marginBottom:'20px'}}>
                    <div className="card" style={{width:'300px'}}>
                        <h3 style={{marginTop:0, display:'flex', alignItems:'center', gap:'10px'}}>
                            <Settings size={20}/> Parametry
                        </h3>
                        <div style={{marginBottom:'20px'}}>
                            <label style={{display:'block', marginBottom:'5px', fontSize:'0.9rem', color:'#64748b'}}>Opóźnienie dostaw (dni)</label>
                            <input type="range" min="0" max="30" value={delayDays} onChange={e=>setDelayDays(e.target.value)} style={{width:'100%'}}/>
                            <div style={{textAlign:'right', fontWeight:'bold'}}>{delayDays} dni</div>
                        </div>
                        <div>
                            <label style={{display:'block', marginBottom:'5px', fontSize:'0.9rem', color:'#64748b'}}>Wzrost popytu (Szok)</label>
                            <input type="range" min="0" max="200" value={demandSpike} onChange={e=>setDemandSpike(e.target.value)} style={{width:'100%'}}/>
                            <div style={{textAlign:'right', fontWeight:'bold'}}>+{demandSpike}%</div>
                        </div>
                    </div>
                    <div className="card" style={{flex:1, height:'400px'}}>
                        <h3 style={{marginTop:0}}>Projekcja Stanów Magazynowych</h3>
                        <ResponsiveContainer>
                            <AreaChart data={scenarios}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false}/>
                                <XAxis dataKey="day"/>
                                <YAxis/>
                                <Tooltip/>
                                <Legend/>
                                <Area type="monotone" dataKey="baseline" name="Bez zmian (Baseline)" stroke="#94a3b8" fill="#f1f5f9" />
                                <Area type="monotone" dataKey="stock" name="Symulacja (Scenario)" stroke="#7c3aed" fill="#8b5cf6" fillOpacity={0.6} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        )}

        {/* --- CHAT --- */}
        <div style={{position:'fixed', bottom:'20px', right:'20px', zIndex:2000}}>
            {!isChatOpen && (
                <button onClick={()=>setIsChatOpen(true)} style={{width:'60px', height:'60px', borderRadius:'50%', background:'#4f46e5', color:'white', border:'none', boxShadow:'0 4px 12px rgba(79, 70, 229, 0.4)', cursor:'pointer', display:'flex', justifyContent:'center', alignItems:'center'}}>
                    <MessageSquare size={28}/>
                </button>
            )}
            {isChatOpen && (
                <div style={{width:'350px', height:'500px', background:'white', borderRadius:'16px', boxShadow:'0 10px 40px rgba(0,0,0,0.2)', display:'flex', flexDirection:'column', overflow:'hidden'}}>
                    <div style={{padding:'15px', background:'#4f46e5', color:'white', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                        <div style={{fontWeight:'bold'}}>Procure-Chat AI</div>
                        <button onClick={()=>setIsChatOpen(false)} style={{background:'transparent', border:'none', color:'white', cursor:'pointer'}}><X size={20}/></button>
                    </div>
                    <div style={{flex:1, padding:'15px', overflowY:'auto', background:'#f8fafc', display:'flex', flexDirection:'column', gap:'10px'}}>
                        {chatMessages.map((msg, i) => (
                            <div key={i} style={{alignSelf: msg.from==='user'?'flex-end':'flex-start', background: msg.from==='user'?'#4f46e5':'white', color: msg.from==='user'?'white':'#1e293b', padding:'10px 14px', borderRadius:'12px', border: msg.from==='bot'?'1px solid #e2e8f0':'none', maxWidth:'80%', fontSize:'0.9rem', whiteSpace:'pre-line'}}>
                                {msg.text}
                            </div>
                        ))}
                        <div ref={chatEndRef}/>
                    </div>
                    <form onSubmit={handleSendMessage} style={{padding:'10px', borderTop:'1px solid #e2e8f0', display:'flex', gap:'10px'}}>
                        <input value={chatInput} onChange={e=>setChatInput(e.target.value)} placeholder="Zapytaj o stan, budżet..." style={{flex:1, border:'1px solid #cbd5e1', borderRadius:'20px', padding:'8px 12px', outline:'none'}}/>
                        <button type="submit" style={{background:'#4f46e5', color:'white', border:'none', borderRadius:'50%', width:'36px', height:'36px', display:'flex', justifyContent:'center', alignItems:'center', cursor:'pointer'}}><Send size={18}/></button>
                    </form>
                </div>
            )}
        </div>

        {/* --- MODAL --- */}
        {selectedOrder && (
            <div style={{
                position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', 
                background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
            }}>
                <div style={{background: 'white', padding: '30px', borderRadius: '12px', width: '650px', maxWidth: '95%', maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)'}}>
                    
                    <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                        <div>
                            <h2 style={{margin:0, display:'flex', alignItems:'center', gap:'10px'}}>
                                Zamówienie {selectedOrder.id}
                                {selectedOrder.id.startsWith('AUTO') && <span style={{fontSize:'0.7rem', background:'#e0f2fe', color:'#0284c7', padding:'2px 6px', borderRadius:'4px'}}>🤖 BOT</span>}
                            </h2>
                            <span style={{color:'#64748b', fontSize:'0.9rem'}}>Utworzono: {new Date(selectedOrder.created_at).toLocaleString()}</span>
                        </div>
                        <button onClick={() => setSelectedOrder(null)} style={{background:'transparent', border:'none', cursor:'pointer'}}><X size={24} color="#64748b"/></button>
                    </div>

                    <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:'20px', marginBottom:'30px'}}>
                        <div style={{background:'#f8fafc', padding:'15px', borderRadius:'8px'}}>
                            <div style={{fontWeight:'bold', marginBottom:'10px', display:'flex', alignItems:'center', gap:'5px', color:'#475569'}}><Package size={16}/> Produkt</div>
                            <div style={{fontWeight:'500'}}>{selectedOrder.product?.name}</div>
                            <div style={{color:'#64748b', fontSize:'0.9rem'}}>{selectedOrder.product?.category}</div>
                            <div style={{marginTop:'5px', fontSize:'0.9rem'}}>Ilość: <strong>{selectedOrder.quantity} {selectedOrder.product?.unit}</strong></div>
                        </div>
                        <div style={{background:'#f8fafc', padding:'15px', borderRadius:'8px'}}>
                            <div style={{fontWeight:'bold', marginBottom:'10px', display:'flex', alignItems:'center', gap:'5px', color:'#475569'}}><Building2 size={16}/> Dostawca</div>
                            <div style={{fontWeight:'500'}}>{selectedOrder.supplier?.name || "Zakup Giełdowy (Spot)"}</div>
                            <div style={{color:'#64748b', fontSize:'0.9rem'}}>Rating: {selectedOrder.supplier?.rating || '-'}/5.0</div>
                            <div style={{marginTop:'5px', fontSize:'0.8rem', color:'#4f46e5'}}>{selectedOrder.supplier ? "Partner Zweryfikowany" : "Dostawca Spot"}</div>
                        </div>
                    </div>

                    <div style={{border:'1px solid #e2e8f0', borderRadius:'8px', padding:'20px', marginBottom:'20px'}}>
                        <div style={{fontWeight:'bold', marginBottom:'15px', display:'flex', alignItems:'center', gap:'5px', color:'#0f172a'}}>
                            <FileSpreadsheet size={18}/> Dane Finansowe (Symulacja Faktury)
                        </div>
                        <div style={{display:'flex', justifyContent:'space-between', marginBottom:'5px', fontSize:'0.95rem'}}>
                            <span style={{color:'#64748b'}}>Wartość Netto:</span>
                            <span>{calculateInvoice(selectedOrder).net.toFixed(2)} PLN</span>
                        </div>
                        <div style={{display:'flex', justifyContent:'space-between', marginBottom:'5px', fontSize:'0.95rem'}}>
                            <span style={{color:'#64748b'}}>VAT (23%):</span>
                            <span>{calculateInvoice(selectedOrder).vat.toFixed(2)} PLN</span>
                        </div>
                        <div style={{display:'flex', justifyContent:'space-between', marginTop:'10px', paddingTop:'10px', borderTop:'1px dashed #e2e8f0', fontWeight:'bold', fontSize:'1.2rem'}}>
                            <span>Do Zapłaty (Brutto):</span>
                            <span style={{color:'#059669'}}>{calculateInvoice(selectedOrder).gross.toFixed(2)} PLN</span>
                        </div>
                    </div>

                    <div style={{background:'#f0fdf4', border:'1px solid #bbf7d0', padding:'15px', borderRadius:'8px', marginBottom:'20px'}}>
                        <div style={{fontWeight:'bold', color:'#166534', display:'flex', alignItems:'center', gap:'5px', marginBottom:'8px'}}>
                            <Banknote size={18}/> Warunki Płatności (Cash Flow)
                        </div>
                        <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.9rem'}}>
                            <span>Termin płatności:</span>
                            <strong>{selectedOrder.payment_terms_days} dni</strong>
                        </div>
                        <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.9rem', marginTop:'4px'}}>
                            <span>Data wymagalności:</span>
                            <strong>{selectedOrder.payment_due_date ? new Date(selectedOrder.payment_due_date).toLocaleDateString() : '-'}</strong>
                        </div>
                    </div>

                    <div style={{display:'flex', gap:'10px', marginTop:'25px', paddingTop:'20px', borderTop:'1px solid #e2e8f0'}}>
                        <button 
                            onClick={() => downloadOrderPDF(selectedOrder.id)} 
                            className="primary-btn" 
                            style={{flex:1, display:'flex', justifyContent:'center', alignItems:'center', gap:'8px', background:'#475569'}}
                        >
                            <FileText size={18}/> Pobierz PO (PDF)
                        </button>
                        
                        {selectedOrder.status === 'pending_approval' && userRole === 'manager' && (
                            <>
                                <button onClick={() => handleApprove(selectedOrder.id)} className="primary-btn" style={{flex:1, background:'#16a34a', display:'flex', justifyContent:'center', alignItems:'center', gap:'8px'}}>
                                    <Check size={18}/> Zatwierdź
                                </button>
                                <button onClick={() => handleReject(selectedOrder.id)} className="primary-btn" style={{flex:1, background:'#dc2626', display:'flex', justifyContent:'center', alignItems:'center', gap:'8px'}}>
                                    <XCircle size={18}/> Odrzuć
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>
        )}

        {/* --- MARKET --- */}
        {activeTab === 'market' && (
            <>
                <div className="card" style={{ marginBottom: '30px', background: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                    <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '10px' }}>
                        <div style={{ position: 'relative', flexGrow: 1 }}>
                            <Search style={{ position: 'absolute', left: '12px', top: '12px', color: '#9ca3af' }} size={20} />
                            <input 
                                type="text" 
                                placeholder="Wpisz potrzebę biznesową (np. 'sprzęt IT', 'artykuły biurowe')..." 
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                style={{ width: '100%', padding: '10px 10px 10px 40px', borderRadius: '6px', border: '1px solid #d1d5db', fontSize: '1rem', boxSizing: 'border-box'}}
                            />
                        </div>
                        <button type="submit" className="primary-btn">Szukaj z AI</button>
                    </form>
                    <div style={{marginTop:'10px', fontSize:'0.85rem', color:'#6b7280'}}>
                        💡 <i>System używa <b>Semantic Search</b>. Wpisz intencję, a nie dokładną nazwę.</i>
                    </div>
                </div>

                {loading ? (
                    <div style={{textAlign:'center', padding:'60px', color:'#94a3b8'}}>🔄 Przeszukiwanie bazy wiedzy...</div>
                ) : (
                    <div className="grid">
                        {products.map((product) => (
                        <div key={product.id} className="card" style={{position:'relative', border: product.active_contract ? '2px solid #10b981' : '1px solid #e2e8f0'}}>
                            {product.active_contract && (
                                <div style={{position:'absolute', top:'12px', right:'12px', color:'#10b981', display:'flex', alignItems:'center', gap:'4px', fontSize:'0.75rem', fontWeight:'700'}}>
                                    <ShieldCheck size={16}/> KONTRAKT
                                </div>
                            )}
                            <h3 style={{margin:'0 0 8px 0', fontSize:'1.1rem'}}>{product.name}</h3>
                            <div style={{display:'flex', gap:'8px', marginBottom:'16px'}}>
                                <span style={{background:'#f1f5f9', padding:'4px 8px', borderRadius:'6px', fontSize:'0.75rem', fontWeight:'600', color:'#475569'}}>
                                    {product.category}
                                </span>
                                {product.current_stock <= product.min_stock_level && (
                                    <span style={{background:'#fee2e2', color:'#dc2626', padding:'4px 8px', borderRadius:'6px', fontSize:'0.75rem', fontWeight:'600'}}>
                                        NISKI STAN
                                    </span>
                                )}
                            </div>
                            <div style={{margin:'15px 0', fontSize:'0.9rem', color:'#4b5563'}}>
                                <div style={{display:'flex', justifyContent:'space-between', marginBottom:'5px'}}>
                                    <span>Stan:</span>
                                    <span style={{fontWeight:'bold', color: product.current_stock <= product.min_stock_level ? '#dc2626' : '#059669'}}>
                                        {product.current_stock} {product.unit}
                                    </span>
                                </div>
                                <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                                    <span>Dostawca:</span>
                                    {product.active_contract ? 
                                        <span style={{color:'#059669', fontWeight:'bold'}}>{product.active_contract.supplier_name}</span> : 
                                        <span style={{color:'#94a3b8', fontStyle:'italic'}}>Spot Market</span>
                                    }
                                </div>
                                {product.active_contract && (
                                    <div style={{textAlign:'right', fontSize:'0.8rem', color:'#059669', marginTop:'2px'}}>
                                        Cena: {product.active_contract.price.toFixed(2)} PLN
                                    </div>
                                )}
                            </div>

                            <div style={{display:'flex', gap:'10px', marginTop:'10px'}}>
                                <button onClick={() => handleOrder(product)} className="primary-btn" style={{flex:1, display:'flex', justifyContent:'center', gap:'8px'}}>
                                    <ShoppingCart size={18} /> Zamów
                                </button>
                                <button 
                                    onClick={() => handleFindAlternatives(product)} 
                                    style={{width:'42px', display:'flex', justifyContent:'center', alignItems:'center', background:'#fff', border:'1px solid #cbd5e1', borderRadius:'8px', cursor:'pointer', color:'#475569'}}
                                    title="Znajdź zamiennik AI"
                                >
                                    <Repeat size={20}/>
                                </button>
                            </div>
                        </div>
                        ))}
                    </div>
                )}
            </>
        )}

        {/* --- INVENTORY --- */}
        {activeTab === 'inventory' && (
            <div className="card" style={{padding:0, overflow:'hidden'}}>
                <div style={{padding:'16px', borderBottom:'1px solid #e2e8f0', display:'flex', justifyContent:'space-between'}}>
                    <div style={{fontWeight:'600'}}>Lista Produktów</div>
                    <button onClick={() => setShowLowStockOnly(!showLowStockOnly)} style={{background:'transparent', border:'none', color: showLowStockOnly ? '#dc2626' : '#64748b', cursor:'pointer', fontWeight:'600', display:'flex', gap:'6px'}}>
                        <Filter size={18}/> {showLowStockOnly ? 'Pokaż Wszystkie' : 'Tylko Krytyczne'}
                    </button>
                </div>
                <table>
                    <thead><tr><th>Produkt</th><th>Kategoria</th><th>Stan / Min</th><th>Wizualizacja</th><th>Akcja</th></tr></thead>
                    <tbody>
                        {inventoryProducts.map(p => {
                            const pct = Math.min(100, (p.current_stock / (p.min_stock_level * 2.5)) * 100);
                            const color = p.current_stock === 0 ? '#dc2626' : p.current_stock <= p.min_stock_level ? '#f59e0b' : '#10b981';
                            return (
                                <tr key={p.id}>
                                    <td style={{fontWeight:'500'}}>{p.name}</td>
                                    <td><span style={{fontSize:'0.75rem', background:'#f1f5f9', padding:'2px 8px', borderRadius:'4px', color:'#475569'}}>{p.category}</span></td>
                                    <td>{p.current_stock} <span style={{color:'#94a3b8'}}>/ {p.min_stock_level}</span></td>
                                    <td style={{width:'30%'}}>
                                        <div style={{height:'6px', background:'#e2e8f0', borderRadius:'3px', overflow:'hidden'}}>
                                            <div style={{width:`${pct}%`, background:color, height:'100%', transition:'width 0.5s'}}/>
                                        </div>
                                    </td>
                                    <td style={{textAlign:'right'}}>
                                        <button onClick={() => handleOrder(p)} style={{background:'transparent', border:'1px solid #cbd5e1', borderRadius:'6px', padding:'4px 10px', cursor:'pointer', fontSize:'0.85rem'}}>Uzupełnij</button>
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
        )}

        {/* --- FORECAST --- */}
        {activeTab === 'forecast' && (
            <div className="card" style={{padding:0, overflow:'hidden'}}>
                <div style={{padding:'24px', borderBottom:'1px solid #e2e8f0', background:'#f8fafc'}}>
                    <h3 style={{margin:0}}>Planowanie MRP (Just-in-Time)</h3>
                    <p style={{margin:'4px 0 0 0', fontSize:'0.85rem', color:'#64748b'}}>System AI analizuje tempo zużycia (Burn Rate) i sugeruje moment zakupu.</p>
                </div>
                {predictions.length === 0 ? <div style={{padding:'40px', textAlign:'center', color:'#94a3b8'}}>Zbieranie danych symulacyjnych...</div> : (
                <table>
                    <thead>
                        <tr style={{background:'#f8fafc'}}>
                            <th>Produkt</th>
                            <th style={{textAlign:'right'}}>Zapas</th>
                            <th style={{textAlign:'right'}}>Zużycie (AI)</th>
                            <th style={{textAlign:'center'}}>Zapas (Dni)</th>
                            <th style={{textAlign:'center'}}>Lead Time</th>
                            <th>Status</th>
                            <th style={{textAlign:'right'}}>Akcja</th>
                        </tr>
                    </thead>
                    <tbody>
                        {predictions.map((pred, i) => {
                            const productInfo = products.find(p => p.id === pred.id);
                            const leadTime = productInfo?.lead_time_days || 7;
                            const buffer = pred.days_left - leadTime;
                            
                            let badge = {bg:'#dcfce7', text:'Bezpieczny', color:'#166534'};
                            if(buffer < 2) badge = {bg:'#fef3c7', text:'Zamów Dziś', color:'#b45309'};
                            if(buffer < 0) badge = {bg:'#fee2e2', text:'KRYTYCZNY', color:'#991b1b'};

                            return (
                                <tr key={i}>
                                    <td style={{fontWeight:'500'}}>{pred.product_name}</td>
                                    <td style={{textAlign:'right'}}>{pred.current_stock}</td>
                                    <td style={{textAlign:'right', fontFamily:'monospace'}}>{pred.burn_rate.toFixed(2)}/d</td>
                                    <td style={{textAlign:'center', fontWeight:'700'}}>{pred.days_left.toFixed(1)}</td>
                                    <td style={{textAlign:'center', color:'#64748b'}}>{leadTime} dni</td>
                                    <td>
                                        <span style={{background:badge.bg, color:badge.color, padding:'4px 8px', borderRadius:'12px', fontSize:'0.75rem', fontWeight:'700', textTransform:'uppercase'}}>{badge.text}</span>
                                    </td>
                                    <td style={{textAlign:'right'}}>
                                        {buffer < 3 && <button onClick={() => handleOrder(pred)} className="primary-btn" style={{padding:'6px 12px', fontSize:'0.8rem'}}>Zamów</button>}
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
                )}
            </div>
        )}

        {/* --- CONTRACTS --- */}
        {activeTab === 'contracts' && (
            <div style={{display:'flex', gap:'40px', alignItems:'flex-start'}}>
                <div className="card" style={{flex:1, textAlign:'center', padding:'40px'}}>
                    <div style={{width:'64px', height:'64px', background:'#e0e7ff', borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center', margin:'0 auto 20px auto'}}>
                        <Upload size={32} color="#4f46e5"/>
                    </div>
                    <h3>Wgraj nową umowę</h3>
                    <p style={{color:'#64748b', marginBottom:'24px'}}>Obsługujemy PDF. AI automatycznie wykona OCR.</p>
                    
                    <input type="file" id="file" onChange={handleFileChange} style={{display:'none'}} accept="application/pdf"/>
                    <label htmlFor="file" className="primary-btn" style={{display:'inline-block', padding:'12px 24px'}}>Wybierz Plik</label>
                    
                    {selectedFile && <div style={{marginTop:'16px', fontWeight:'600'}}>{selectedFile.name}</div>}
                    {selectedFile && !contractDraft && (
                        <button onClick={analyzeContract} disabled={uploading} style={{marginTop:'16px', width:'100%', background:'#0f172a', color:'white', border:'none', padding:'12px', borderRadius:'8px', cursor:'pointer'}}>
                            {uploading ? 'Analizowanie...' : 'Uruchom AI OCR'}
                        </button>
                    )}
                </div>

                {contractDraft && (
                    <div className="card" style={{flex:1, border:'2px solid #10b981'}}>
                        <div style={{display:'flex', alignItems:'center', gap:'10px', color:'#10b981', marginBottom:'20px'}}>
                            <CheckCircle size={24}/>
                            <h3 style={{margin:0}}>Analiza Zakończona</h3>
                        </div>
                        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:'20px', marginBottom:'24px'}}>
                            <div><div style={{fontSize:'0.8rem', color:'#64748b'}}>Dostawca</div><div style={{fontWeight:'600', fontSize:'1.1rem'}}>{contractDraft.supplier_name}</div></div>
                            <div><div style={{fontSize:'0.8rem', color:'#64748b'}}>Produkt</div><div style={{fontWeight:'600', fontSize:'1.1rem'}}>{contractDraft.product_name}</div></div>
                            <div><div style={{fontSize:'0.8rem', color:'#64748b'}}>Cena</div><div style={{fontWeight:'600', fontSize:'1.1rem', color:'#059669'}}>{contractDraft.price} PLN</div></div>
                            <div><div style={{fontSize:'0.8rem', color:'#64748b'}}>Ważność</div><div style={{fontWeight:'600', fontSize:'1.1rem'}}>{contractDraft.valid_until.split('T')[0]}</div></div>
                        </div>
                        <button onClick={confirmContract} className="primary-btn" style={{width:'100%', background:'#10b981'}}>Zatwierdź i Dodaj do Compliance</button>
                    </div>
                )}
            </div>
        )}

        {/* --- ORDERS (Z NOWYM PANELEM LOGÓW!) --- */}
        {activeTab === 'orders' && (
            <div style={{display:'grid', gridTemplateColumns:'2fr 1fr', gap:'20px', alignItems:'start'}}>
                <div className="card" style={{padding:0, overflow:'hidden'}}>
                    <div style={{padding:'20px', borderBottom:'1px solid #e2e8f0', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                        <h3>Wszystkie Zamówienia</h3>
                        <button onClick={fetchOrders} style={{background:'transparent', border:'none', cursor:'pointer'}}><RefreshCw size={20}/></button>
                    </div>
                    <table>
                        <thead>
                            <tr><th style={{paddingLeft:'20px'}}>ID</th><th>Produkt</th><th>Wartość</th><th>Status</th><th style={{textAlign:'right', paddingRight:'20px'}}>Szczegóły</th></tr>
                        </thead>
                        <tbody>
                            {orders.map(o => (
                                <tr key={o.id} onClick={() => setSelectedOrder(o)} style={{cursor:'pointer', borderBottom:'1px solid #f1f5f9', background: o.status === 'pending_approval' ? '#fff7ed' : 'white'}}>
                                    <td style={{padding:'16px 20px', fontFamily:'monospace', fontWeight:'600'}}>
                                        {o.id} {o.id.startsWith('AUTO') && <span style={{fontSize:'0.7rem', color:'#3b82f6'}}>🤖 BOT</span>}
                                    </td>
                                    <td>{o.product?.name}</td>
                                    <td>{o.total_price.toFixed(2)} PLN</td>
                                    <td>
                                        {o.status === 'pending_approval' && <span className="status-badge" style={{background:'#ffedd5', color:'#c2410c'}}>⏳ Akceptacja</span>}
                                        {o.status === 'ordered' && <span className="status-badge" style={{background:'#e0f2fe', color:'#0369a1'}}>📦 Złożono</span>}
                                        {o.status === 'delivered' && <span className="status-badge" style={{background:'#dcfce7', color:'#15803d'}}>✅ Dostarczono</span>}
                                        {o.status === 'cancelled' && <span className="status-badge" style={{background:'#fee2e2', color:'#b91c1c'}}>❌ Odrzucono</span>}
                                    </td>
                                    <td style={{textAlign:'right', paddingRight:'20px'}}>
                                        <Info size={18} color="#94a3b8"/>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {/* --- LIVE EVENT FEED (NOWOŚĆ) --- */}
                <div className="card" style={{padding:'0', maxHeight:'600px', display:'flex', flexDirection:'column', background:'#1e293b', color:'white', border:'none'}}>
                    <div style={{padding:'15px', borderBottom:'1px solid #334155', display:'flex', alignItems:'center', gap:'10px'}}>
                        <Terminal size={20} color="#4ade80"/>
                        <h3 style={{margin:0, color:'white', fontSize:'1rem'}}>Dziennik Zdarzeń (Live)</h3>
                    </div>
                    <div style={{padding:'15px', overflowY:'auto', flex:1, fontFamily:'monospace', fontSize:'0.85rem'}}>
                        {simulationStatus?.events && simulationStatus.events.length > 0 ? (
                            simulationStatus.events.map((ev) => (
                                <div key={ev.id} style={{marginBottom:'10px', paddingBottom:'10px', borderBottom:'1px dashed #334155'}}>
                                    <div style={{color:'#94a3b8', fontSize:'0.75rem', marginBottom:'2px'}}>[{ev.date}]</div>
                                    <div style={{display:'flex', gap:'8px', alignItems:'start'}}>
                                        <span>{ev.icon}</span>
                                        <span style={{color: ev.type === 'warning' ? '#fca5a5' : ev.type === 'error' ? '#ef4444' : '#e2e8f0'}}>
                                            {ev.message}
                                        </span>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div style={{color:'#64748b', textAlign:'center', marginTop:'20px'}}>Oczekiwanie na zdarzenia...<br/>(Włącz symulację)</div>
                        )}
                    </div>
                </div>
            </div>
        )}

       
        {activeTab === 'analytics' && (
            <div>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'30px'}}>
                    <h3>Centrum Analityczne AI</h3>
                    <button onClick={downloadReport} className="primary-btn" style={{display:'flex', alignItems:'center', gap:'8px'}}><Download size={18}/> Eksportuj PDF</button>
                </div>
                
                {!analyticsData ? (
                    <div style={{textAlign:'center', padding:'40px', color:'#94a3b8'}}>Ładowanie danych BI...</div>
                ) : (
                    <>
                        {/* KPI CARDS */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                            <div className="card" style={{borderLeft:'4px solid #10b981'}}>
                                <div style={{display:'flex', justifyContent:'space-between', alignItems:'start'}}>
                                    <div>
                                        <p style={{fontSize:'0.85rem', color:'#64748b', fontWeight:'600'}}>Zrealizowane Wydatki</p>
                                        <p style={{fontSize:'1.8rem', fontWeight:'bold', margin:'5px 0'}}>
                                            {analyticsData.security.approved_value.toLocaleString()} PLN
                                        </p>
                                    </div>
                                    <div style={{background:'#dcfce7', padding:'8px', borderRadius:'8px'}}>
                                        <DollarSign size={24} color="#15803d"/>
                                    </div>
                                </div>
                            </div>

                            <div className="card" style={{borderLeft:'4px solid #ef4444'}}>
                                <div style={{display:'flex', justifyContent:'space-between', alignItems:'start'}}>
                                    <div>
                                        <p style={{fontSize:'0.85rem', color:'#64748b', fontWeight:'600'}}>Oszczędność (Cost Avoidance)</p>
                                        <p style={{fontSize:'1.8rem', fontWeight:'bold', margin:'5px 0', color:'#dc2626'}}>
                                            {analyticsData.security.blocked_value.toLocaleString()} PLN
                                        </p>
                                        <p style={{fontSize:'0.75rem', color:'#ef4444'}}>
                                            AI zablokowało {analyticsData.security.fraud_rate}% transakcji
                                        </p>
                                    </div>
                                    <div style={{background:'#fee2e2', padding:'8px', borderRadius:'8px'}}>
                                        <Shield size={24} color="#b91c1c"/>
                                    </div>
                                </div>
                            </div>

                            <div className="card" style={{borderLeft:'4px solid #3b82f6'}}>
                                <div style={{display:'flex', justifyContent:'space-between', alignItems:'start'}}>
                                    <div>
                                        <p style={{fontSize:'0.85rem', color:'#64748b', fontWeight:'600'}}>Wartość Magazynu</p>
                                        <p style={{fontSize:'1.8rem', fontWeight:'bold', margin:'5px 0'}}>
                                            {analyticsData.inventory.reduce((acc, curr) => acc + curr.value, 0).toLocaleString()} PLN
                                        </p>
                                    </div>
                                    <div style={{background:'#dbeafe', padding:'8px', borderRadius:'8px'}}>
                                        <TrendingUp size={24} color="#1d4ed8"/>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Wykres Bezpieczeństwa */}
                            <div className="card" style={{height:'400px'}}>
                                <h4 style={{marginTop:0}}>Skuteczność AI Auditora (Isolation Forest)</h4>
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={[
                                        { name: 'Zatwierdzone', value: analyticsData.security.approved_value, fill: '#10B981' },
                                        { name: 'Zablokowane', value: analyticsData.security.blocked_value, fill: '#EF4444' }
                                    ]}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                        <XAxis dataKey="name" />
                                        <YAxis />
                                        <Tooltip formatter={(value) => `${value.toLocaleString()} PLN`} />
                                        <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={60} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>

                            {/* Wykres Magazynu */}
                            <div className="card" style={{height:'400px'}}>
                                <h4 style={{marginTop:0}}>Top Produkty Zamrażające Kapitał</h4>
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart layout="vertical" data={analyticsData.inventory} margin={{ left: 20 }}>
                                        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                        <XAxis type="number" hide />
                                        <YAxis dataKey="name" type="category" width={100} style={{ fontSize: '11px' }} />
                                        <Tooltip formatter={(value) => `${value.toLocaleString()} PLN`} />
                                        <Bar dataKey="value" fill="#3B82F6" radius={[0, 4, 4, 0]} barSize={20} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        {/* Stare wykresy historyczne */}
                        <div className="grid grid-cols-1 gap-6 mt-6">
                            <div className="card" style={{height:'350px'}}>
                                <h4 style={{marginTop:0}}>Dynamika Zapasów (Historyczna)</h4>
                                <ResponsiveContainer>
                                    <AreaChart data={history}>
                                        <defs>
                                            <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.8}/>
                                                <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false}/>
                                        <XAxis dataKey="shortDate" fontSize={12}/>
                                        <YAxis fontSize={12}/>
                                        <Tooltip/>
                                        <Area type="monotone" dataKey="total_items" stroke="#4f46e5" fillOpacity={1} fill="url(#colorTotal)"/>
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </>
                )}
            </div>
        )}

      </div>
    </div>
  )
}

export default App