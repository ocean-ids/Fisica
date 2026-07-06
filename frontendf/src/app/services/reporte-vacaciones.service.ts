import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { ReporteVacaciones } from '../models/reporte-vacaciones.model';

@Injectable({
  providedIn: 'root',
})
export class ReporteVacacionesService {
  constructor(private api: ApiService) {}

  listar(): Observable<ReporteVacaciones[]> {
    return this.api.get<ReporteVacaciones[]>('/reporte-vacaciones/');
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
