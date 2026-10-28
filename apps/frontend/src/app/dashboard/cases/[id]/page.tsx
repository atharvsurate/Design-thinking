"use client";
import { ArrowLeft, FileText, Upload, Lock, Eye, Download, ShieldCheck, Tag } from "lucide-react";

export default function CaseDetails({ params }: { params: { id: string } }) {
  const documents = [
    { id: "DOC-8831", name: "Seizure_Memo_Laptop.pdf", type: "SEIZURE_MEMO", size: "2.4 MB", date: "Today, 10:42 AM", evidence: true, privileged: false },
    { id: "DOC-8830", name: "WhatsApp_Chat_Extract_TargetA.csv", type: "FORENSIC_REPORT", size: "14.1 MB", date: "Yesterday, 14:15 PM", evidence: true, privileged: false },
    { id: "DOC-8824", name: "Legal_Strategy_Memo_Draft.docx", type: "INTELLIGENCE_MEMO", size: "1.2 MB", date: "Sep 12, 2026", evidence: false, privileged: true },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center space-x-4">
        <a href="/dashboard" className="p-2 bg-white border border-slate-200 rounded-md hover:bg-slate-50 text-slate-500">
          <ArrowLeft size={20} />
        </a>
        <div>
          <h1 className="text-2xl font-bold text-slate-800">{decodeURIComponent(params.id)}</h1>
          <p className="text-slate-500 text-sm">Operation Silken Thread - Financial Fraud</p>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 flex justify-between items-center">
        <div className="flex space-x-8">
          <div><p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Vault KEK</p><p className="font-mono text-sm text-slate-700 mt-1 flex items-center"><Lock size={14} className="mr-1 text-emerald-500"/> transit/keys/case-cbi-42</p></div>
          <div><p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Lead IO</p><p className="font-medium text-sm text-slate-700 mt-1">Insp. R. Kumar (CBI)</p></div>
          <div><p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Storage</p><p className="font-medium text-sm text-slate-700 mt-1">NIC MeghRaj (IN-NIC-1)</p></div>
        </div>
        <button className="flex items-center px-4 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 shadow-sm transition-colors">
          <Upload size={18} className="mr-2" /> Upload Evidence
        </button>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center bg-slate-50/50">
          <Search className="text-slate-400 mr-2" size={18} />
          <input type="text" placeholder="Search decrypted text via OpenSearch (Hindi/English)..." className="bg-transparent border-none outline-none w-full text-sm text-slate-700 placeholder-slate-400" />
        </div>
        <table className="w-full text-left text-sm text-slate-600">
          <thead className="bg-slate-50 text-slate-500 uppercase text-xs font-semibold border-b border-slate-200">
            <tr>
              <th className="px-6 py-3">Document Name</th>
              <th className="px-6 py-3">Type</th>
              <th className="px-6 py-3">Security Tags</th>
              <th className="px-6 py-3">Size & Date</th>
              <th className="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {documents.map((doc, i) => (
              <tr key={i} className="hover:bg-slate-50">
                <td className="px-6 py-4">
                  <div className="flex items-center">
                    <FileText className="text-slate-400 mr-3" size={20} />
                    <span className="font-medium text-slate-900">{doc.name}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-xs font-medium text-slate-500">{doc.type.replace('_', ' ')}</td>
                <td className="px-6 py-4 flex flex-wrap gap-2">
                  {doc.evidence && (
                    <span className="px-2 py-1 rounded bg-amber-100 text-amber-800 border border-amber-200 text-[10px] font-bold tracking-wider flex items-center">
                      <Lock size={10} className="mr-1"/> WORM EVIDENCE
                    </span>
                  )}
                  {doc.privileged && (
                    <span className="px-2 py-1 rounded bg-red-100 text-red-800 border border-red-200 text-[10px] font-bold tracking-wider flex items-center">
                      <ShieldCheck size={10} className="mr-1"/> PRIVILEGED
                    </span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <p className="text-slate-900 font-medium">{doc.size}</p>
                  <p className="text-xs text-slate-400">{doc.date}</p>
                </td>
                <td className="px-6 py-4 text-right space-x-2">
                  <button className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors" title="View (Watermarked)">
                    <Eye size={18} />
                  </button>
                  <button className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors" title="Export Chain of Custody PDF">
                    <ShieldCheck size={18} />
                  </button>
                  <button className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors" title="Download Decrypted">
                    <Download size={18} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
