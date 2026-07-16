import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpParams } from '@angular/common/http';
import { ApiService } from './api.service';
import { ReportePago, TarifaPago } from '../models/reporte-pago.model';

@Injectable({
  providedIn: 'root',
})
export class ReportePagoService {
  constructor(private api: ApiService) {}

  // --- Reporte de pagos (deriva del reporte de guardia) ---
  listar(fecha: string, turno?: string): Observable<ReportePago[]> {
    let params = new HttpParams().set('fecha', fecha);
    if (turno) { params = params.set('turno', turno); }
    return this.api.get<ReportePago[]>('/reporte-pago/', params);
  }
  actualizar(id: number, data: Partial<ReportePago>): Observable<ReportePago> {
    return this.api.put(`/reporte-pago/${id}/`, data);
  }

  // --- Tarifas (editor) ---
  listarTarifas(): Observable<TarifaPago[]> { return this.api.get<TarifaPago[]>('/tarifas-pago/'); }
  listarTipos(): Observable<string[]> { return this.api.get<string[]>('/tarifas-pago/tipos/'); }
  crearTarifa(data: TarifaPago): Observable<TarifaPago> { return this.api.post('/tarifas-pago/crear/', data); }
  actualizarTarifa(id: number, data: Partial<TarifaPago>): Observable<TarifaPago> { return this.api.put(`/tarifas-pago/${id}/`, data); }
  eliminarTarifa(id: number): Observable<any> { return this.api.delete(`/tarifas-pago/${id}/eliminar/`); }
}
