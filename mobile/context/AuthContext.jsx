import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { setUnauthorizedHandler } from '../services/api';
import { clearAccessToken, getAccessToken, saveAccessToken } from '../services/session';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [status, setStatus] = useState('loading');
  const [sessionNotice, setSessionNotice] = useState('');

  const signOut = useCallback(async () => {
    try {
      await clearAccessToken();
    } finally {
      setSessionNotice('');
      setStatus('anonymous');
    }
  }, []);

  const expireSession = useCallback(async () => {
    try {
      await clearAccessToken();
    } finally {
      setSessionNotice('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
      setStatus('anonymous');
    }
  }, []);

  const signIn = useCallback(async (token) => {
    await saveAccessToken(token);
    setSessionNotice('');
    setStatus('authenticated');
  }, []);

  useEffect(() => {
    let active = true;

    getAccessToken()
      .then((token) => {
        if (active) setStatus(token ? 'authenticated' : 'anonymous');
      })
      .catch(() => {
        if (active) setStatus('anonymous');
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(expireSession);
    return () => setUnauthorizedHandler(null);
  }, [expireSession]);

  const clearSessionNotice = useCallback(() => setSessionNotice(''), []);
  const value = useMemo(
    () => ({ status, signIn, signOut, sessionNotice, clearSessionNotice }),
    [status, signIn, signOut, sessionNotice, clearSessionNotice]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth phải được dùng bên trong AuthProvider');
  return context;
}
