import { FileSearch, Shield, AlertTriangle, Users } from "lucide-react";

export default function Dashboard() {
  const cases = [
    { id: "CBI-2026-0042", title: "Operation Silken Thread - Financial Fraud", date: "Sep 12, 2026", status: "ACTIVE", docs: 142, class: "SECRET" },
    { id: "DP-2026-8991", title: "FIR 49/2026 - Cyber Espionage Incident", date: "Aug 04, 2026", status: "ACTIVE", docs: 38, class: "TOP_SECRET" },
    { id: "NIA-2025-104", title: "Cross-border Smuggling Intercept", date: "Dec 19, 2025", status: "LEGAL_HOLD", docs: 412, class: "CONFIDENTIAL" },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex items-center">
          <div className="p-3 bg-blue-100 text-blue-600 rounded-md mr-4"><Folder size={20} /></div>
          <div><p className="text-sm text-slate-500 font-medium">Active Cases</p><p className="text-2xl font-bold">12</p></div>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex items-center">
          <div className="p-3 bg-indigo-100 text-indigo-600 rounded-md mr-4"><FileSearch size={20} /></div>
          <div><p className="text-sm text-slate-500 font-medium">Documents</p><p className="text-2xl font-bold">1,842</p></div>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex items-center">
          <div className="p-3 bg-amber-100 text-amber-600 rounded-md mr-4"><AlertTriangle size={20} /></div>
          <div><p className="text-sm text-slate-500 font-medium">Pending Approvals</p><p className="text-2xl font-bold">3</p></div>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex items-center">
          <div className="p-3 bg-emerald-100 text-emerald-600 rounded-md mr-4"><Shield size={20} /></div>
          <div><p className="text-sm text-slate-500 font-medium">Audit Integrity</p><p className="text-xl font-bold text-emerald-600">VERIFIED</p></div>
        </div>
      </div>

      {/* Case Table */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-slate-800">My Assigned Cases</h2>
          <button className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors">
            + Open New Case
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50 text-slate-500 uppercase text-xs font-semibold">
              <tr>
                <th className="px-6 py-3">Case ID</th>
                <th className="px-6 py-3">Title / Subject</th>
                <th className="px-6 py-3">Classification</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3 text-center">Docs</th>
                <th className="px-6 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {cases.map((c, i) => (
                <tr key={i} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4 font-medium text-slate-900">{c.id}</td>
                  <td className="px-6 py-4">{c.title}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-xs font-bold ${
                      c.class === 'TOP_SECRET' ? 'bg-red-100 text-red-800 border-red-200' :
                      c.class === 'SECRET' ? 'bg-orange-100 text-orange-800 border-orange-200' :
                      'bg-slate-100 text-slate-800 border-slate-200'
                    } border`}>
                      {c.class}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      c.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-purple-100 text-purple-700'
                    }`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center font-medium">{c.docs}</td>
                  <td className="px-6 py-4 text-right">
                    <a href={`/dashboard/cases/${c.id}`} className="text-blue-600 hover:text-blue-800 font-medium">Open Case &rarr;</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
