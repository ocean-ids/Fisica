import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { ReporteVacaciones } from '../models/reporte-vacaciones.model';

@Injectable({
  providedIn: 'root',
})
export class ReporteVacacionesService {
  constructor(private api: ApiService) {}

  listar(tipo?: 'VACACIONES' | 'BACKUP'): Observable<ReporteVacaciones[]> {
    const qs = tipo ? `?tipo=${tipo}` : '';
    return this.api.get<ReporteVacaciones[]>(`/reporte-vacaciones/${qs}`);
  }

  // IDs de personas (fijos) con asignacion activa en el mes/anio.
  personasAsignadas(mes: number, anio: number): Observable<{ persona_ids: number[] }> {
    return this.api.get(`/personas-asignadas/${mes}/${anio}/`);
  }

  // Asignacion activa de una persona (cliente/instalacion/puesto) para autocargar en el form.
  asignacionDePersona(personaId: number): Observable<{
    asignacion_id: number; cliente: string; instalacion: string; puesto: string;
    anio: number; mes: number;
  }> {
    return this.api.get(`/asignaciones/de-persona/${personaId}/`);
  }

  crear(data: ReporteVacaciones): Observable<ReporteVacaciones> {
    return this.api.post('/reporte-vacaciones/crear/', data);
  }

  actualizar(id: number, data: Partial<ReporteVacaciones>): Observable<ReporteVacaciones> {
    return this.api.put(`/reporte-vacaciones/${id}/`, data);
  }

  eliminar(id: number): Observable<any> {
    return this.api.delete(`/reporte-vacaciones/${id}/eliminar/`);
  }
}
