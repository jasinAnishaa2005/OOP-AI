import { create } from 'zustand';

import { authApi, type RegisterInput, type TokenResponse, type User } from '@/api/auth';
import { ApiError } from '@/api/client';
import { secureStorage } from '@/lib/secureStorage';

const REFRESH_KEY = 'oopai.refreshToken';

/** Offline, rate-limited or server errors: the refresh token may still be valid, so keep it. */
const isTransient = (error: unknown) =>
  error instanceof ApiError && (error.status === 0 || error.status === 429 || error.status >= 500);

type Status = 'loading' | 'signedOut' | 'signedIn';

type AuthState = {
  status: Status;
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  persist: boolean;
  hydrate: () => Promise<void>;
  signIn: (identifier: string, password: string, rememberMe: boolean) => Promise<void>;
  signUp: (input: RegisterInput) => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => Promise<string | null>;
};

export const useAuthStore = create<AuthState>((set, get) => {
  const applyTokens = async (tokens: TokenResponse, persist: boolean) => {
    if (persist) await secureStorage.set(REFRESH_KEY, tokens.refresh_token);
    else await secureStorage.remove(REFRESH_KEY);
    set({
      status: 'signedIn',
      user: tokens.user,
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      persist,
    });
  };

  const clear = async () => {
    await secureStorage.remove(REFRESH_KEY);
    set({ status: 'signedOut', user: null, accessToken: null, refreshToken: null, persist: false });
  };

  return {
    status: 'loading',
    user: null,
    accessToken: null,
    refreshToken: null,
    persist: false,

    hydrate: async () => {
      const stored = await secureStorage.get(REFRESH_KEY).catch(() => null);
      if (!stored) {
        set({ status: 'signedOut' });
        return;
      }
      try {
        await applyTokens(await authApi.refresh(stored), true);
      } catch (error) {
        if (isTransient(error)) {
          // Keep the stored session so the next launch can retry.
          set({ status: 'signedOut' });
          return;
        }
        await clear();
      }
    },

    signIn: async (identifier, password, rememberMe) => {
      const tokens = await authApi.login({ identifier: identifier.trim(), password, remember_me: rememberMe });
      await applyTokens(tokens, rememberMe);
    },

    signUp: async (input) => {
      await applyTokens(await authApi.register(input), true);
    },

    signOut: async () => {
      const { accessToken, refreshToken } = get();
      if (accessToken || refreshToken) await authApi.logout(accessToken, refreshToken).catch(() => undefined);
      await clear();
    },

    refresh: async () => {
      const { refreshToken, persist } = get();
      if (!refreshToken) return null;
      try {
        const tokens = await authApi.refresh(refreshToken);
        await applyTokens(tokens, persist);
        return tokens.access_token;
      } catch (error) {
        if (!isTransient(error)) await clear();
        return null;
      }
    },
  };
});
