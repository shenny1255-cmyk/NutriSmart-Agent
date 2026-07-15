import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';

export default function AdminAudit() {
    const [logs, setLogs] = useState([]);

    useEffect(() => { api.auditLogs().then(setLogs).catch(() => { }); }, []);

    return (
        <div className= "space-y-6" >
        <h1 className="text-2xl font-bold" > Nhật ký hệ thống </h1>
            < div className = "overflow-hidden rounded-xl border border-slate-200 bg-white" >
                <table className="w-full text-sm" >
                    <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500" >
                        <tr>
                        <th className="px-4 py-3" > Thời gian </th>
                            < th className = "px-4 py-3" > Hành động </th>
                                < th className = "px-4 py-3" > Đối tượng </th>
                                    < th className = "px-4 py-3" > ID </th>
                                        </tr>
                                        </thead>
                                        <tbody>
    {
        logs.map((l) => (
            <tr key= { l.id } className = "border-t border-slate-100" >
            <td className="px-4 py-3" > { new Date(l.created_at).toLocaleString('vi-VN') } </td>
        < td className = "px-4 py-3" >
        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs" > { l.action } </span>
        </td>
        < td className = "px-4 py-3" > { l.entity } </td>
        < td className = "px-4 py-3 text-xs text-slate-500" > { l.entity_id || '—' } </td>
        </tr>
        ))
    }
    </tbody>
        </table>
        </div>
        </div>
  );
}