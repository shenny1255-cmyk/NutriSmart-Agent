import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';
import { TableShell, THead, Tr, Td, EmptyRow } from '../components/ui.jsx';

export default function AdminAudit() {
    const [logs, setLogs] = useState([]);

    useEffect(() => { api.auditLogs().then(setLogs).catch(() => { }); }, []);

    return (
        <div className="space-y-6">
            <h1 className="font-display text-2xl font-bold tracking-tight">Nhật ký hệ thống</h1>

            <TableShell>
                <THead cols={['Thời gian', 'Hành động', 'Đối tượng', 'ID']} />
                <tbody>
                    {logs.length === 0 && <EmptyRow colSpan={4}>Chưa có bản ghi nào.</EmptyRow>}
                    {logs.map((l) => (
                        <Tr key={l.id}>
                            <Td className="whitespace-nowrap text-ink-2">
                                {new Date(l.created_at).toLocaleString('vi-VN')}
                            </Td>
                            <Td>
                                <span className="rounded-full bg-paper-3 px-2.5 py-0.5 font-mono text-xs text-ink-2">
                                    {l.action}
                                </span>
                            </Td>
                            <Td>{l.entity}</Td>
                            <Td className="font-mono text-xs text-muted">{l.entity_id || '—'}</Td>
                        </Tr>
                    ))}
                </tbody>
            </TableShell>
        </div>
    );
}