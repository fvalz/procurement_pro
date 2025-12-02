import { useState, useEffect } from 'react'
import axios from 'axios'
import { 
    ShoppingCart, Package, RefreshCw, AlertTriangle, Search, 
    FileText, Upload, CheckCircle, Clock, Truck, CheckSquare, ShieldCheck,
    Boxes, Filter, BarChart3, TrendingUp, CalendarRange, Zap, UserCircle, Download, XCircle, Check, BrainCircuit
} from 'lucide-react'
import { 
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    BarChart, Bar, Legend, Line, ComposedChart
} from 'recharts';

function App() {
  // --- STANY APLIKACJI ---
  const [activeTab, setActiveTab] = useState('market') // 'market' | 'inventory' | 'contracts' | 'orders' | 'analytics' | 'forecast'
  const [userRole, setUserRole] = useState('employee') // 'employee' | 'manager'
  
  const [products, setProducts] = useState([])
  const [orders, setOrders] = useState([])
  const [history, setHistory] = useState([]) 
  const [predictions, setPredictions] = useState([]) 
  const [simulationStatus, setSimulationStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [showLowStockOnly, setShowLowStockOnly] = useState(false)
  
  // Stany dla Smart Wallet (Kontrakty)
  const [selectedFile, setSelectedFile] = useState(null)
  const [contractDraft, setContractDraft] = useState(null)
  const [uploading, setUploading] = useState(false)

  const API_URL = 'http://127.0.0.1:8000'

  // --- POBIERANIE DANYCH ---
  useEffect(() => {
    fetchSimulationStatus()
    fetchProducts()
    
    const interval = setInterval(() => {
        fetchSimulationStatus()
        
        // Inteligentne odświeżanie w zależności od zakładki
        if (activeTab === 'orders') fetchOrders()
        if (activeTab === 'inventory') fetchProducts()
        if (activeTab === 'analytics') { fetchHistory(); fetchPredictions(); }
        if (activeTab === 'forecast') { fetchPredictions(); }
    }, 1000)
    
    return () => clearInterval(interval)
  }, [activeTab])

  const fetchProducts = async (query = "") => {
    // Nie pokazujemy loading spinnera przy auto-odświeżaniu w tych zakładkach
    if (!['inventory', 'orders', 'analytics', 'forecast'].includes(activeTab)) setLoading(true)
        
    try {
      const endpoint = query 
        ? `${API_URL}/products?search=${query}&limit=100`
        : `${API_URL}/products?limit=100`
      const response = await axios.get(endpoint)
      setProducts(response.data)
    } catch (error) { console.error("Błąd produktów:", error) } finally { setLoading(false) }
  }

  const fetchOrders = async () => {
      try {
          const response = await axios.get(`${API_URL}/orders?limit=50`)
          setOrders(response.data)
      } catch (error) { console.error("Błąd zamówień:", error) }
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

  const fetchSimulationStatus = async () => {
    try {
      const response = await axios.get(`${API_URL}/simulation/status`)
      setSimulationStatus(response.data)
    } catch (error) { console.error(error) }
  }

  // --- AKCJE ---

  const toggleSimulation = async () => {
    const endpoint = simulationStatus?.is_running ? '/simulation/stop' : '/simulation/start'
    await axios.post(`${API_URL}${endpoint}`)
    fetchSimulationStatus()
  }

  const handleOrder = async (item) => {
    // Dzięki zmianom w backendzie, item (czy to produkt czy predykcja) zawsze ma ID
    let pid = item.id 
    let name = item.name || item.product_name

    const qty = prompt(`Podaj ilość do zamówienia (${name}):`, "20")
    if (!qty) return

    try {
      await axios.post(`${API_URL}/orders`, {
        product_id: pid,
        quantity: parseFloat(qty),
        order_type: "standard"
      })
      alert("✅ Zamówienie wysłane!")
      fetchOrders()
    } catch (error) { alert("Błąd: " + error.message) }
  }

  // Akcje Managera
  const handleApprove = async (orderId) => {
      try { await axios.put(`${API_URL}/orders/${orderId}/approve`); fetchOrders(); } catch(e) { alert(e.message) }
  }
  const handleReject = async (orderId) => {
      try { await axios.put(`${API_URL}/orders/${orderId}/reject`); fetchOrders(); } catch(e) { alert(e.message) }
  }

  const downloadReport = () => {
      window.open(`${API_URL}/analytics/report/pdf`, '_blank')
  }

  const handleSearchSubmit = (e) => { e.preventDefault(); fetchProducts(searchQuery); }
  const handleFileChange = (e) => { setSelectedFile(e.target.files[0]); setContractDraft(null); }
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
      } catch (error) { alert(error.message) } finally { setUploading(false) }
  }
  const confirmContract = async () => {
      try { await axios.post(`${API_URL}/contracts/confirm`, contractDraft); alert("✅ Kontrakt dodany!"); setContractDraft(null); setSelectedFile(null) } catch (error) { alert(error.message) }
  }

  const inventoryProducts = showLowStockOnly ? products.filter(p => p.current_stock <= p.min_stock_level) : products

  return (
    <div style={{ minHeight: '100vh', paddingBottom: '50px' }}>
      {/* HEADER */}
      <div className="header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Package size={32} color="#2563eb" />
          <div>
            <h1 style={{ margin: 0, fontSize: '1.5rem' }}>Procurement Pro</h1>
            <span style={{fontSize:'0.8rem', color:'#6b7280', letterSpacing: '1px'}}>ENTERPRISE AI SUITE</span>
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
            {/* PRZEŁĄCZNIK RÓL (WORKFLOW) */}
            <div style={{ background: '#e0e7ff', padding: '5px 10px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <UserCircle size={20} color="#4f46e5"/>
                <select 
                    value={userRole} 
                    onChange={(e) => setUserRole(e.target.value)}
                    style={{ background: 'transparent', border: 'none', fontWeight: 'bold', color: '#3730a3', cursor: 'pointer' }}
                >
                    <option value="employee">Pracownik</option>
                    <option value="manager">Manager (Admin)</option>
                </select>
            </div>

            {/* PANEL SYMULACJI */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px', background: '#f8fafc', padding: '8px 16px', borderRadius: '20px', border: '1px solid #e2e8f0' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                    <span style={{ fontSize: '0.7rem', fontWeight: 'bold', color: '#64748b' }}>SYMULACJA</span>
                    <span style={{ fontFamily: 'monospace', fontSize: '1.1rem', color: '#0f172a' }}>
                        {simulationStatus?.current_date || '...'}
                    </span>
                </div>
                <button onClick={toggleSimulation} className={simulationStatus?.is_running ? 'secondary' : ''}>
                    {simulationStatus?.is_running ? '⏸️' : '▶️'}
                </button>
            </div>
        </div>
      </div>

      <div className="container">
        
        {/* NAWIGACJA (TABS) */}
        <div style={{ display: 'flex', gap: '10px', marginBottom: '30px', flexWrap: 'wrap' }}>
            <button className={activeTab === 'market' ? '' : 'secondary'} onClick={() => setActiveTab('market')} style={{flex:1}}>
                <Search size={18}/> Marketplace AI
            </button>
            <button className={activeTab === 'inventory' ? '' : 'secondary'} onClick={() => setActiveTab('inventory')} style={{flex:1}}>
                <Boxes size={18}/> Magazyn
            </button>
            <button className={activeTab === 'contracts' ? '' : 'secondary'} onClick={() => setActiveTab('contracts')} style={{flex:1}}>
                <FileText size={18}/> Smart Wallet
            </button>
            <button className={activeTab === 'orders' ? '' : 'secondary'} onClick={() => {setActiveTab('orders'); fetchOrders();}} style={{flex:1}}>
                <Clock size={18}/> Operacje
            </button>
            <button className={activeTab === 'analytics' ? '' : 'secondary'} onClick={() => {setActiveTab('analytics'); fetchHistory();}} style={{flex:1}}>
                <BarChart3 size={18}/> Raporty
            </button>
            <button className={activeTab === 'forecast' ? '' : 'secondary'} onClick={() => {setActiveTab('forecast'); fetchPredictions();}} style={{flex:1}}>
                <CalendarRange size={18}/> Prognoza AI
            </button>
        </div>

        {/* --- TAB 1: MARKET --- */}
        {activeTab === 'market' && (
            <>
                <div style={{ marginBottom: '30px', background: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                    <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '10px' }}>
                        <div style={{ position: 'relative', flexGrow: 1 }}>
                            <Search style={{ position: 'absolute', left: '12px', top: '12px', color: '#9ca3af' }} size={20} />
                            <input 
                                type="text" 
                                placeholder="Opisz potrzebę biznesową (np. 'coś do pisania', 'sprzęt IT')..." 
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                style={{ width: '100%', padding: '10px 10px 10px 40px', borderRadius: '6px', border: '1px solid #d1d5db', fontSize: '1rem', boxSizing: 'border-box'}}
                            />
                        </div>
                        <button type="submit">Szukaj AI</button>
                    </form>
                    <div style={{ marginTop: '10px', fontSize: '0.85rem', color: '#6b7280' }}>
                        💡 <i>System używa <b>Semantic Search</b>. Wpisz intencję, a nie dokładną nazwę.</i>
                    </div>
                </div>

                {loading ? <div style={{textAlign:'center', padding:'40px', color:'#6b7280'}}>🔄 Przeszukiwanie bazy wiedzy...</div> : (
                    <div className="grid">
                        {products.map((product) => (
                        <div key={product.id} className="card" style={{ border: product.active_contract ? '2px solid #10b981' : '1px solid #e5e7eb', position: 'relative' }}>
                            {product.active_contract && (
                                <div style={{ position: 'absolute', top: '-10px', right: '10px', background: '#10b981', color: 'white', padding: '4px 8px', borderRadius: '12px', fontSize: '0.7rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '4px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                                    <ShieldCheck size={14} /> KONTRAKT
                                </div>
                            )}
                            <h3 style={{ margin: '0 0 5px 0', fontSize: '1.1rem', paddingRight: '20px' }}>{product.name}</h3>
                            <span style={{ fontSize: '0.8rem', background: '#f1f5f9', padding: '2px 8px', borderRadius: '4px' }}>{product.category}</span>
                            <div style={{ margin: '15px 0', fontSize: '0.9rem', color: '#4b5563' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                                    <span>Stan:</span>
                                    <span style={{ fontWeight: 'bold', color: product.current_stock <= product.min_stock_level ? '#dc2626' : '#059669' }}>{product.current_stock} {product.unit}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: product.active_contract ? '#ecfdf5' : 'transparent', padding: '4px', borderRadius: '4px' }}>
                                    <span>Dostawca:</span>
                                    {product.active_contract ? <span style={{ color: '#047857', fontWeight: 'bold', fontSize: '0.85rem' }}>{product.active_contract.supplier_name}</span> : <span style={{ color: '#9ca3af', fontStyle: 'italic' }}>Giełda (Spot)</span>}
                                </div>
                                {product.active_contract && <div style={{ textAlign: 'right', fontSize: '0.8rem', color: '#059669', marginTop: '2px' }}>Cena: {product.active_contract.price.toFixed(2)} PLN</div>}
                            </div>
                            <button onClick={() => handleOrder(product)} style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: '8px' }}><ShoppingCart size={18} /> Zamów</button>
                        </div>
                        ))}
                    </div>
                )}
            </>
        )}

        {/* --- TAB 2: INVENTORY --- */}
        {activeTab === 'inventory' && (
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}><Boxes size={24} /> Stany Magazynowe</h2>
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <button className={!showLowStockOnly ? 'secondary' : ''} onClick={() => setShowLowStockOnly(!showLowStockOnly)} style={{ background: showLowStockOnly ? '#fee2e2' : '', color: showLowStockOnly ? '#b91c1c' : '', border: showLowStockOnly ? '1px solid #f87171' : '' }}>
                            <Filter size={16} style={{marginRight: '5px'}}/> {showLowStockOnly ? 'Krytyczne' : 'Wszystkie'}
                        </button>
                        <button className="secondary" onClick={() => fetchProducts()}><RefreshCw size={16}/> Odśwież</button>
                    </div>
                </div>
                <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                        <thead style={{ background: '#f1f5f9' }}>
                            <tr><th style={{ padding: '15px', textAlign: 'left' }}>Produkt</th><th style={{ padding: '15px', textAlign: 'left' }}>Kategoria</th><th style={{ padding: '15px', textAlign: 'left', width: '250px' }}>Dostępność</th><th style={{ padding: '15px', textAlign: 'left' }}>Status</th><th style={{ padding: '15px', textAlign: 'right' }}>Akcja</th></tr>
                        </thead>
                        <tbody>
                            {inventoryProducts.map((p) => {
                                const percentage = Math.min(100, (p.current_stock / (p.min_stock_level * 2)) * 100);
                                const isLow = p.current_stock <= p.min_stock_level;
                                const isCritical = p.current_stock === 0;
                                return (
                                    <tr key={p.id} style={{ borderBottom: '1px solid #e2e8f0', background: isLow ? '#fff1f2' : 'white' }}>
                                        <td style={{ padding: '15px', fontWeight: '500' }}>{p.name}</td>
                                        <td style={{ padding: '15px' }}><span style={{ fontSize: '0.75rem', background: '#f1f5f9', padding: '2px 8px', borderRadius: '4px', color: '#475569' }}>{p.category}</span></td>
                                        <td style={{ padding: '15px' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem' }}>
                                                <div style={{ flexGrow: 1, height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                                                    <div style={{ width: `${percentage}%`, height: '100%', background: isCritical ? '#dc2626' : (isLow ? '#f59e0b' : '#10b981'), transition: 'width 0.5s' }}></div>
                                                </div>
                                                <span style={{ fontWeight: 'bold', color: isLow ? '#b91c1c' : '#1f2937', minWidth: '60px', textAlign: 'right' }}>{p.current_stock} / {p.min_stock_level}</span>
                                            </div>
                                        </td>
                                        <td style={{ padding: '15px' }}>{isCritical ? <span style={{ color: '#dc2626', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '5px' }}><AlertTriangle size={14}/> BRAK!</span> : isLow ? <span style={{ color: '#d97706', fontWeight: 'bold' }}>Niski</span> : <span style={{ color: '#059669' }}>OK</span>}</td>
                                        <td style={{ padding: '15px', textAlign: 'right' }}><button onClick={() => handleOrder(p)} className={isLow ? '' : 'secondary'} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>Uzupełnij</button></td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        )}

        {/* --- TAB 3: CONTRACTS --- */}
        {activeTab === 'contracts' && (
            <div style={{ maxWidth: '600px', margin: '0 auto' }}>
                <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
                    <FileText size={48} color="#2563eb" style={{ marginBottom: '20px' }} />
                    <h2>Cyfryzacja Umów</h2>
                    <div style={{ border: '2px dashed #cbd5e1', padding: '30px', borderRadius: '8px', margin: '20px 0', background: '#f8fafc' }}>
                        <input type="file" accept="application/pdf" onChange={handleFileChange} />
                    </div>
                    {selectedFile && !contractDraft && (
                        <button onClick={analyzeContract} disabled={uploading} style={{ width: '100%' }}>{uploading ? 'Analizowanie...' : 'Analizuj PDF'}</button>
                    )}
                    {contractDraft && (
                        <div style={{ marginTop: '20px', textAlign: 'left', background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '20px', borderRadius: '8px' }}>
                            <h3>Wynik Analizy:</h3>
                            <p><strong>Produkt:</strong> {contractDraft.product_name}</p>
                            <p><strong>Dostawca:</strong> {contractDraft.supplier_name}</p>
                            <p><strong>Cena:</strong> {contractDraft.price} PLN</p>
                            <button onClick={confirmContract} style={{ width: '100%', marginTop: '10px', background: '#166534' }}>✅ Zatwierdź</button>
                        </div>
                    )}
                </div>
            </div>
        )}

        {/* --- TAB 4: ORDERS --- */}
        {activeTab === 'orders' && (
            <div>
                <div className="card" style={{ padding: 0 }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                        <thead style={{ background: '#f1f5f9' }}>
                            <tr><th style={{padding:'10px'}}>ID</th><th>Produkt</th><th>Wartość</th><th>Status</th><th>Akcja (Manager)</th></tr>
                        </thead>
                        <tbody>
                            {orders.map((order) => (
                                <tr key={order.id} style={{ borderBottom: '1px solid #e2e8f0', background: order.status === 'pending_approval' ? '#fff7ed' : 'white' }}>
                                    <td style={{padding:'10px', fontWeight: 'bold'}}>{order.id} {order.id.startsWith('AUTO') && <span style={{fontSize:'0.7rem', color:'#0284c7'}}>🤖 AUTO</span>}</td>
                                    <td style={{padding:'10px'}}>{order.product?.name}</td>
                                    <td style={{padding:'10px'}}>{order.total_price.toFixed(2)} PLN</td>
                                    <td style={{padding:'10px'}}>
                                        {order.status === 'pending_approval' ? <span style={{color:'#d97706', fontWeight:'bold'}}>⏳ Czeka na akceptację</span> :
                                         order.status === 'delivered' ? <span style={{color:'green'}}>✅ Dostarczono</span> : 
                                         order.status === 'cancelled' ? <span style={{color:'red'}}>❌ Odrzucono</span> : '🚚 W drodze'}
                                    </td>
                                    <td style={{padding:'10px', textAlign:'right'}}>
                                        {order.status === 'pending_approval' && userRole === 'manager' && (
                                            <div style={{display:'flex', gap:'5px', justifyContent:'flex-end'}}>
                                                <button onClick={() => handleApprove(order.id)} style={{background:'#16a34a', padding:'4px 8px'}}><Check size={16}/></button>
                                                <button onClick={() => handleReject(order.id)} style={{background:'#dc2626', padding:'4px 8px'}}><XCircle size={16}/></button>
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        )}

        {/* --- TAB 5: ANALYTICS --- */}
        {activeTab === 'analytics' && (
            <div>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'20px'}}>
                    <h2>Analityka</h2>
                    <button onClick={downloadReport} style={{background:'#4f46e5', display:'flex', alignItems:'center', gap:'8px'}}><Download size={16}/> Pobierz Raport PDF</button>
                </div>
                {history.length === 0 ? <div style={{padding:'40px', textAlign:'center'}}>Zbieranie danych...</div> : (
                    <div className="grid">
                        <div className="card" style={{ height: '350px' }}>
                            <h3>Dynamika Zapasów</h3>
                            <ResponsiveContainer><AreaChart data={history}><XAxis dataKey="shortDate"/><YAxis/><Tooltip/><Area type="monotone" dataKey="total_items" stroke="#8884d8" fill="#8884d8" /></AreaChart></ResponsiveContainer>
                        </div>
                        <div className="card" style={{ height: '350px' }}>
                            <h3>Analiza Ryzyka</h3>
                            <ResponsiveContainer><ComposedChart data={history}><XAxis dataKey="shortDate"/><YAxis/><Tooltip/><Bar dataKey="low_stock_count" fill="#ff7300" /><Line type="monotone" dataKey="pending_orders" stroke="#387908" /></ComposedChart></ResponsiveContainer>
                        </div>
                    </div>
                )}
            </div>
        )}

        {/* --- TAB 6: FORECAST (AI MRP) --- */}
        {activeTab === 'forecast' && (
            <div>
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px'}}>
                    <h2 style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                        <CalendarRange color="#7c3aed"/> Prognoza Planistyczna (AI)
                    </h2>
                    <button className="secondary" onClick={fetchPredictions}><RefreshCw size={16}/> Odśwież</button>
                </div>

                {predictions.length === 0 ? (
                    <div style={{padding: '40px', textAlign: 'center', color: '#6b7280'}}>
                        <p>AI uczy się tempa zużycia... Uruchom symulację.</p>
                    </div>
                ) : (
                    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                            <thead style={{ background: '#f8fafc', color: '#64748b' }}>
                                <tr>
                                    <th style={{ padding: '15px', textAlign: 'left' }}>Produkt</th>
                                    <th style={{ padding: '15px', textAlign: 'right' }}>Zapas</th>
                                    <th style={{ padding: '15px', textAlign: 'right' }}>Zużycie (AI Forecast)</th>
                                    <th style={{ padding: '15px', textAlign: 'center' }}>Zapas na (dni)</th>
                                    <th style={{ padding: '15px', textAlign: 'center' }}>Lead Time</th>
                                    <th style={{ padding: '15px', textAlign: 'left' }}>Status / Plan</th>
                                    <th style={{ padding: '15px', textAlign: 'right' }}>Akcja</th>
                                </tr>
                            </thead>
                            <tbody>
                                {predictions.map((pred, idx) => {
                                    const productInfo = products.find(p => p.id === pred.id) // Używamy ID do matchowania
                                    const leadTime = productInfo?.lead_time_days || 7 
                                    const bufferDays = pred.days_left - leadTime
                                    
                                    let rowBg = 'white'
                                    let statusText = ''
                                    let statusColor = '#64748b'

                                    if (bufferDays < 0) {
                                        rowBg = '#fef2f2'; statusText = `🚨 KRYTYCZNE! (-${Math.abs(Math.floor(bufferDays))} dni)`; statusColor = '#dc2626'
                                    } else if (bufferDays < 2) {
                                        rowBg = '#fffbeb'; statusText = "⚠️ Zamawiaj dzisiaj"; statusColor = '#d97706'
                                    } else {
                                        statusText = `Bezpieczny (ok. ${Math.floor(bufferDays)} dni)`; statusColor = '#059669'
                                    }

                                    return (
                                        <tr key={idx} style={{ borderBottom: '1px solid #e2e8f0', background: rowBg }}>
                                            <td style={{ padding: '15px', fontWeight: 'bold' }}>{pred.product_name}</td>
                                            <td style={{ padding: '15px', textAlign: 'right' }}>{pred.current_stock}</td>
                                            <td style={{ padding: '15px', textAlign: 'right' }}>~{pred.burn_rate.toFixed(2)}/dzień</td>
                                            <td style={{ padding: '15px', textAlign: 'center' }}>
                                                <span style={{background: pred.days_left < leadTime ? '#fee2e2' : '#e0f2fe', padding: '4px 8px', borderRadius: '10px', fontSize:'0.85rem', color: pred.days_left < leadTime ? '#b91c1c' : '#0369a1', fontWeight:'bold'}}>
                                                    {pred.days_left.toFixed(1)}
                                                </span>
                                            </td>
                                            <td style={{ padding: '15px', textAlign: 'center' }}>{leadTime} dni</td>
                                            <td style={{ padding: '15px', fontWeight: 'bold', color: statusColor }}>{statusText}</td>
                                            <td style={{ padding: '15px', textAlign: 'right' }}>
                                                {bufferDays < 3 && <button onClick={() => handleOrder(pred)} style={{background: bufferDays < 0 ? '#dc2626' : '#2563eb', padding:'6px 12px', fontSize:'0.8rem'}}>Zamów</button>}
                                            </td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        )}

      </div>
    </div>
  )
}

export default App