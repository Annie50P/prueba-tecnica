import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Clientes from './pages/Clientes';
import ClienteDetalle from './pages/ClienteDetalle';
import Agentes from './pages/Agentes';
import AgenteDetalle from './pages/AgenteDetalle';
import Grafo from './pages/Grafo';
import Analisis from './pages/Analisis';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="clientes" element={<Clientes />} />
        <Route path="clientes/:id" element={<ClienteDetalle />} />
        <Route path="agentes" element={<Agentes />} />
        <Route path="agentes/:id" element={<AgenteDetalle />} />
        <Route path="grafo" element={<Grafo />} />
        <Route path="analisis" element={<Analisis />} />
      </Route>
    </Routes>
  );
}
