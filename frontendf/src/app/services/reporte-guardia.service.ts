import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpParams } from '@angular/common/http';
import { ApiService } from './api.service';
import { ReporteGuardia } from '../models/reporte-guardia.model';

@Injectable({
  providedIn: 'root',
})
export class ReporteGuardiaService {
  constructor(private api: ApiService){}

  listar(fecha: string, turno?: string): Observable<ReporteGuardia[]> {
    let params = new HttpParams().set('fecha', fecha);
    if (turno) params = params.set('turno', turno);
    return this.api.get<ReporteGuardia[]>('/reporte-guardia/', params);
  }
  
  crear(data: ReporteGuardia): Observable<ReporteGuardia> { return this.api.post('/reporte-guardia/crear/', data); }
  actualizar(id: number, data: Partial<ReporteGuardia>): Observable<ReporteGuardia> { return this.api.put(`/reporte-guardia/${id}/`, data); }
  eliminar(id: number): Observable<any> { return this.api.delete(`/reporte-guardia/${id}/eliminar/`); }
}
