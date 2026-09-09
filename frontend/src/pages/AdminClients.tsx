import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Client } from '../types';
import { 
  Plus, Search, Edit2, Trash2, Eye, ToggleLeft, ToggleRight, 
  AlertTriangle, Loader2, RefreshCw, X, ShieldAlert, Ban
} from 'lucide-react';

export default function AdminClients() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters and Sorting
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [planFilter, setPlanFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState<keyof Client>('company_name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  
  // Form States
  const [companyName, setCompanyName] = useState('');
  const [contactName, setContactName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [industry, setIndustry] = useState('');
  const [plan, setPlan] = useState('PRO');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState<'ACTIVE' | 'INACTIVE' | 'SUSPENDED'>('ACTIVE');
  const [formError, setFormError] = useState<string | null>(null);
  const [formLoading, setFormLoading] = useState(false);

  const navigate = useNavigate();

  const fetchClients = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getClients();
      setClients(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch clients list.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClients();
  }, []);

  const resetForm = () => {
    setCompanyName('');
    setContactName('');
    setEmail('');
    setPhone('');
    setIndustry('');
    setPlan('PRO');
    setPassword('');
    setStatus('ACTIVE');
    setFormError(null);
  };

  const handleAddClient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim() || !contactName.trim() || !email.trim() || !password.trim()) {
      setFormError('Please fill in all required fields (Company, Contact, Email, Password)');
      return;
    }

    setFormLoading(true);
    setFormError(null);
    try {
      await api.createClient({
        company_name: companyName.trim(),
        contact_name: contactName.trim(),
        email: email.trim(),
        phone: phone.trim(),
        industry: industry.trim(),
        plan,
        password,
        status
      });
      setShowAddModal(false);
      resetForm();
      fetchClients();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create client.');
    } finally {
      setFormLoading(false);
    }
  };

  const handleEditClick = (client: Client) => {
    setSelectedClient(client);
    setCompanyName(client.company_name);
    setContactName(client.contact_name);
    setEmail(client.email);
    setPhone(client.phone || '');
    setIndustry(client.industry || '');
    setPlan(client.plan || 'PRO');
    setStatus(client.status);
    setPassword(''); // Leave blank unless changing
    setFormError(null);
    setShowEditModal(true);
  };

  const handleEditClient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClient) return;

    setFormLoading(true);
    setFormError(null);
    try {
      const payload: any = {
        company_name: companyName.trim(),
        contact_name: contactName.trim(),
        email: email.trim(),
        phone: phone.trim(),
        industry: industry.trim(),
        plan,
        status
      };
      if (password) {
        payload.password = password;
      }
      await api.updateClient(selectedClient.id, payload);
      setShowEditModal(false);
      setSelectedClient(null);
      resetForm();
      fetchClients();
    } catch (err: any) {
      setFormError(err.message || 'Failed to update client.');
    } finally {
      setFormLoading(false);
    }
  };

  const toggleClientStatus = async (client: Client, newStatus: 'ACTIVE' | 'INACTIVE' | 'SUSPENDED') => {
    try {
      await api.updateClient(client.id, { status: newStatus });
      fetchClients();
    } catch (err: any) {
      alert(`Error updating client status: ${err.message}`);
    }
  };

  const handleDeleteClient = async (id: number) => {
    if (!confirm('Are you absolutely sure you want to delete this client? This will permanently drop all their isolated datasets, metrics, and reports.')) {
      return;
    }
    try {
      await api.deleteClient(id);
      fetchClients();
    } catch (err: any) {
      alert(`Error deleting client: ${err.message}`);
    }
  };

  // Sort and Filter Logics
  const handleSort = (field: keyof Client) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  const filteredClients = clients
    .filter((c) => {
      const matchesSearch = 
        c.company_name.toLowerCase().includes(search.toLowerCase()) ||
        c.contact_name.toLowerCase().includes(search.toLowerCase()) ||
        c.email.toLowerCase().includes(search.toLowerCase());
      
      const matchesStatus = statusFilter === 'ALL' || c.status === statusFilter;
      const matchesPlan = planFilter === 'ALL' || c.plan === planFilter;
      
      return matchesSearch && matchesStatus && matchesPlan;
    })
    .sort((a, b) => {
      let valA = a[sortBy] ?? '';
      let valB = b[sortBy] ?? '';
      if (typeof valA === 'string') valA = valA.toLowerCase();
      if (typeof valB === 'string') valB = valB.toLowerCase();

      if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
      if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

  return (
    <div className="p-8 space-y-8 overflow-y-auto h-[calc(100vh-80px)]">
      {/* Header Panel */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-100 tracking-tight">Client CRM Management</h2>
          <p className="text-xs text-slate-400">Configure client profiles, active subscription plans, passwords, and service levels</p>
        </div>
        <button
          onClick={() => { resetForm(); setShowAddModal(true); }}
          className="px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/10 flex items-center gap-1.5 cursor-pointer active:scale-98 transition-all"
        >
          <Plus className="h-4 w-4" />
          Add Client
        </button>
      </div>

      {/* Filters Pane */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-5 glass-panel rounded-xl border border-slate-800/80">
        <div className="relative md:col-span-2">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
            <Search className="h-4 w-4" />
          </span>
          <input
            type="text"
            placeholder="Search company, contact, or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-900/40 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 transition"
          />
        </div>
        <div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900/40 border border-slate-800 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50"
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active Only</option>
            <option value="INACTIVE">Inactive Only</option>
            <option value="SUSPENDED">Suspended Only</option>
          </select>
        </div>
        <div>
          <select
            value={planFilter}
            onChange={(e) => setPlanFilter(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900/40 border border-slate-800 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50"
          >
            <option value="ALL">All Plans</option>
            <option value="FREE">Free Plan</option>
            <option value="PRO">Pro Plan</option>
            <option value="ENTERPRISE">Enterprise Plan</option>
          </select>
        </div>
      </div>

      {/* Main CRM Table */}
      <div className="glass-panel rounded-xl border border-slate-800 overflow-hidden">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <Loader2 className="h-8 w-8 text-indigo-500 animate-spin" />
            <p className="text-xs text-slate-400 font-semibold">Syncing clients database...</p>
          </div>
        ) : filteredClients.length === 0 ? (
          <div className="text-center py-20 space-y-2">
            <ShieldAlert className="h-8 w-8 text-slate-600 mx-auto" />
            <p className="text-xs text-slate-400 font-semibold">No clients matching active filters</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/20 text-slate-400 text-[10px] font-bold tracking-wider uppercase">
                  <th className="py-3.5 pl-5 cursor-pointer hover:text-slate-200" onClick={() => handleSort('company_name')}>Company</th>
                  <th className="py-3.5 cursor-pointer hover:text-slate-200" onClick={() => handleSort('contact_name')}>Contact Person</th>
                  <th className="py-3.5">Email</th>
                  <th className="py-3.5">Industry</th>
                  <th className="py-3.5 cursor-pointer hover:text-slate-200" onClick={() => handleSort('plan')}>Plan</th>
                  <th className="py-3.5 cursor-pointer hover:text-slate-200" onClick={() => handleSort('status')}>Status</th>
                  <th className="py-3.5">Last Login</th>
                  <th className="py-3.5 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40 text-xs font-semibold text-slate-300">
                {filteredClients.map((client) => {
                  const statusColors = {
                    ACTIVE: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
                    INACTIVE: 'bg-slate-500/10 border-slate-500/20 text-slate-400',
                    SUSPENDED: 'bg-rose-500/10 border-rose-500/20 text-rose-400',
                  };
                  return (
                    <tr key={client.id} className="hover:bg-slate-800/20 transition">
                      <td className="py-4 pl-5 font-bold text-slate-100">{client.company_name}</td>
                      <td className="py-4 text-slate-200">{client.contact_name}</td>
                      <td className="py-4 text-slate-400">{client.email}</td>
                      <td className="py-4 text-slate-400">{client.industry || '—'}</td>
                      <td className="py-4">
                        <span className="px-2.5 py-1 rounded bg-slate-800/80 border border-slate-700 text-[10px] uppercase font-bold text-slate-300">
                          {client.plan}
                        </span>
                      </td>
                      <td className="py-4">
                        <span className={`px-2.5 py-1.5 rounded-full border text-[10px] uppercase tracking-wide font-bold ${statusColors[client.status]}`}>
                          {client.status}
                        </span>
                      </td>
                      <td className="py-4 text-slate-500">
                        {client.last_login ? new Date(client.last_login).toLocaleString() : 'Never'}
                      </td>
                      <td className="py-4 text-center">
                        <div className="flex justify-center items-center gap-1.5">
                          <button
                            onClick={() => navigate(`/admin/clients/${client.id}`)}
                            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition"
                            title="View Client Details"
                          >
                            <Eye className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleEditClick(client)}
                            className="p-1.5 text-slate-400 hover:text-indigo-400 hover:bg-indigo-500/10 rounded transition"
                            title="Edit Client"
                          >
                            <Edit2 className="h-4 w-4" />
                          </button>
                          {client.status === 'ACTIVE' ? (
                            <button
                              onClick={() => toggleClientStatus(client, 'SUSPENDED')}
                              className="p-1.5 text-slate-400 hover:text-amber-400 hover:bg-amber-500/10 rounded transition"
                              title="Suspend Client"
                            >
                              <Ban className="h-4 w-4" />
                            </button>
                          ) : (
                            <button
                              onClick={() => toggleClientStatus(client, 'ACTIVE')}
                              className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 rounded transition"
                              title="Activate Client"
                            >
                              <ToggleLeft className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            onClick={() => handleDeleteClient(client.id)}
                            className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded transition"
                            title="Delete Client"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Client Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-xl glass-panel border border-slate-800 rounded-2xl overflow-hidden shadow-2xl relative">
            <button
              onClick={() => setShowAddModal(false)}
              className="absolute top-4 right-4 p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800/80 transition"
            >
              <X className="h-4 w-4" />
            </button>
            <div className="p-6 border-b border-slate-800">
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">Register New Client Account</h3>
              <p className="text-[10px] text-slate-400">Creates company profile and links a CLIENT-role login account</p>
            </div>
            
            <form onSubmit={handleAddClient} className="p-6 space-y-4">
              {formError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-medium">
                  {formError}
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Company Name *</label>
                  <input
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g. Acme Corp"
                    className="w-full px-3.5 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Contact Name *</label>
                  <input
                    type="text"
                    required
                    value={contactName}
                    onChange={(e) => setContactName(e.target.value)}
                    placeholder="e.g. John Doe"
                    className="w-full px-3.5 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Email Address *</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="john@acme.com"
                    className="w-full px-3.5 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Phone Number</label>
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+1 (555) 019-9234"
                    className="w-full px-3.5 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Industry</label>
                  <input
                    type="text"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    placeholder="e.g. Logistics"
                    className="w-full px-3.5 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Subscription Plan</label>
                  <select
                    value={plan}
                    onChange={(e) => setPlan(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50"
                  >
                    <option value="FREE">Free Plan</option>
                    <option value="PRO">Pro Plan</option>
                    <option value="ENTERPRISE">Enterprise Plan</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Default Password *</label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-3.5 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Initial Status</label>
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value as any)}
                    className="w-full px-3 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50"
                  >
                    <option value="ACTIVE">Active</option>
                    <option value="INACTIVE">Inactive</option>
                    <option value="SUSPENDED">Suspended</option>
                  </select>
                </div>
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-slate-800/80">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border border-slate-800 hover:bg-slate-800 text-slate-300 rounded-lg text-xs font-semibold transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-indigo-600/10 cursor-pointer disabled:opacity-50"
                >
                  {formLoading ? 'Creating...' : 'Save Profile'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Client Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-xl glass-panel border border-slate-800 rounded-2xl overflow-hidden shadow-2xl relative">
            <button
              onClick={() => { setShowEditModal(false); setSelectedClient(null); }}
              className="absolute top-4 right-4 p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800/80 transition"
            >
              <X className="h-4 w-4" />
            </button>
            <div className="p-6 border-b border-slate-800">
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">Modify Client Profile</h3>
              <p className="text-[10px] text-slate-400">Updating metadata settings for client ID {selectedClient?.id}</p>
            </div>
            
            <form onSubmit={handleEditClient} className="p-6 space-y-4">
              {formError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-xl font-medium">
                  {formError}
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Company Name</label>
                  <input
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Contact Person</label>
                  <input
                    type="text"
                    required
                    value={contactName}
                    onChange={(e) => setContactName(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Email Address</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Phone Number</label>
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Industry</label>
                  <input
                    type="text"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="w-full px-3.5 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Subscription Plan</label>
                  <select
                    value={plan}
                    onChange={(e) => setPlan(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50"
                  >
                    <option value="FREE">Free Plan</option>
                    <option value="PRO">Pro Plan</option>
                    <option value="ENTERPRISE">Enterprise Plan</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Update Password (Optional)</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Leave blank to keep same"
                    className="w-full px-3.5 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase">Account Status</label>
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value as any)}
                    className="w-full px-3 py-2 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50"
                  >
                    <option value="ACTIVE">Active</option>
                    <option value="INACTIVE">Inactive</option>
                    <option value="SUSPENDED">Suspended</option>
                  </select>
                </div>
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-slate-800/80">
                <button
                  type="button"
                  onClick={() => { setShowEditModal(false); setSelectedClient(null); }}
                  className="px-4 py-2 border border-slate-800 hover:bg-slate-800 text-slate-300 rounded-lg text-xs font-semibold transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-indigo-600/10 cursor-pointer disabled:opacity-50"
                >
                  {formLoading ? 'Saving...' : 'Apply Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
