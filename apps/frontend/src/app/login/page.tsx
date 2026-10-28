"use client";
import { Shield, Lock } from "lucide-react";

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center text-blue-500">
          <Shield size={64} />
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-white">
          Ministry of Home Affairs
        </h2>
        <p className="mt-2 text-center text-sm text-slate-400">
          Secure Digital Document Management System
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-800 py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-slate-700">
          <form className="space-y-6" action="/dashboard" method="GET">
            <div>
              <label className="block text-sm font-medium text-slate-300">NIC Employee ID / NIC-AD</label>
              <div className="mt-1">
                <input required className="appearance-none block w-full px-3 py-2 border border-slate-600 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm bg-slate-700 text-white" defaultValue="NIC-994321" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300">Passcode / MFA Token</label>
              <div className="mt-1 relative">
                <input type="password" required className="appearance-none block w-full px-3 py-2 border border-slate-600 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm bg-slate-700 text-white" defaultValue="********" />
                <Lock className="absolute right-3 top-2.5 h-4 w-4 text-slate-400" />
              </div>
            </div>

            <div>
              <button type="submit" className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 focus:ring-offset-slate-900 transition-colors">
                Authenticate via NIC
              </button>
            </div>
            
            <div className="mt-4 text-center">
              <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Protected by AES-256-GCM & Ed25519 Audit Chain</span>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
