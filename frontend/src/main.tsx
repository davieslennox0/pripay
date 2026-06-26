import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SuiClientProvider, WalletProvider } from '@mysten/dapp-kit'
import { getJsonRpcFullnodeUrl } from '@mysten/sui/jsonRpc'
import '@mysten/dapp-kit/dist/index.css'
import './index.css'
import App from './App.tsx'
import { umbraWalletTheme } from './lib/walletTheme.ts'

const SUI_NETWORK = (import.meta.env.VITE_SUI_NETWORK as string) ?? 'testnet'

const queryClient = new QueryClient()
const networks = {
  [SUI_NETWORK]: {
    url: getJsonRpcFullnodeUrl(SUI_NETWORK as 'testnet'),
    network: SUI_NETWORK,
  },
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <SuiClientProvider networks={networks} defaultNetwork={SUI_NETWORK}>
        <WalletProvider autoConnect slushWallet={{ name: 'Umbra' }} theme={umbraWalletTheme}>
          <App />
        </WalletProvider>
      </SuiClientProvider>
    </QueryClientProvider>
  </StrictMode>,
)
