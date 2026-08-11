import { Injectable } from '@angular/core';
import { ApiService } from './api.service';

export interface ZonaOperativa {
  id: number;
  numero: number;
  nombre: string;
  nominativos_count?: number;
}

export interface Nominativo {
  id: number;
  zona: number;
  zona_numero?: number;
  zona_nombre?: string;
  letra: string;
  numero: number;
  codigo?: string;
  instalacion: number | null;
  instalacion_nombre?: string;
  cliente_nombre?: string;
}

@Injectable({ providedIn: 'root' })
export class NominativoService {
  constructor(private api: ApiService) {}

  // --- Zonas ---
  getZonas() {
    return this.api.get<ZonaOperativa[]>('/zonas-operativas/');
  }
  crearZona(data: { numero: number; nombre?: string }) {
    return this.api.post<ZonaOperativa>('/zonas-operativas/crear/', data);
  }
  actualizarZona(id: number, data: { numero?: number; nombre?: string }) {
    return this.api.put<ZonaOperativa>(`/zonas-operativas/${id}/`, data);
  }
  eliminarZona(id: number) {
    return this.api.delete<{ message: string }>(`/zonas-operativas/${id}/eliminar/`);
  }

  // --- Nominativos ---
  getNominativos(params?: { zona_id?: number; q?: string }) {
    // Construir params limpio: NO enviar claves vacías/undefined (si no, el backend
    // recibiría q=undefined y buscaría el texto "undefined" -> lista vacía).
    const p: any = {};
    if (params?.zona_id != null) p.zona_id = params.zona_id;
    if (params?.q) p.q = params.q;
    return this.api.get<Nominativo[]>('/nominativos/', p);
  }
  crearNominativo(data: { zona: number; letra: string; numero: number; instalacion?: number | null }) {
    return this.api.post<Nominativo>('/nominativos/crear/', data);
  }
  actualizarNominativo(id: number, data: Partial<{ zona: number; letra: string; numero: number; instalacion: number | null }>) {
    return this.api.put<Nominativo>(`/nominativos/${id}/`, data);
  }
  eliminarNominativo(id: number) {
    return this.api.delete<{ message: string }>(`/nominativos/${id}/eliminar/`);
  }
}
