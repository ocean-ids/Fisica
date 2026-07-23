import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpParams } from '@angular/common/http';
import { ApiService } from './api.service';
import { ReportePago, TarifaPago, ResumenMensualPago } from '../models/reporte-pago.model';

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

  // Resumen del mes: total general, total por tipo de servicio y total por persona.
  // Si se pasa tipoServicio, solo se cuenta/muestra ese tipo.
  resumenMensual(mes: number, anio: number, tipoServicio?: string): Observable<ResumenMensualPago> {
    let params = new HttpParams().set('mes', String(mes)).set('anio', String(anio));
    if (tipoServicio) { params = params.set('tipo_servicio', tipoServicio); }
    return this.api.get<ResumenMensualPago>('/reporte-pago/resumen-mensual/', params);
  }

  // Desglose de una persona en el mes (los pagos que suman su total).
  detallePersonaMes(mes: number, anio: number, personaId: number, tipoServicio?: string): Observable<ReportePago[]> {
    let params = new HttpParams()
      .set('mes', String(mes)).set('anio', String(anio)).set('persona_id', String(personaId));
    if (tipoServicio) { params = params.set('tipo_servicio', tipoServicio); }
    return this.api.get<ReportePago[]>('/reporte-pago/detalle-persona/', params);
  }

  // --- Tarifas (editor) ---
  listarTarifas(): Observable<TarifaPago[]> { return this.api.get<TarifaPago[]>('/tarifas-pago/'); }
  listarTipos(): Observable<string[]> { return this.api.get<string[]>('/tarifas-pago/tipos/'); }
  crearTarifa(data: TarifaPago): Observable<TarifaPago> { return this.api.post('/tarifas-pago/crear/', data); }
  actualizarTarifa(id: number, data: Partial<TarifaPago>): Observable<TarifaPago> { return this.api.put(`/tarifas-pago/${id}/`, data); }
  eliminarTarifa(id: number): Observable<any> { return this.api.delete(`/tarifas-pago/${id}/eliminar/`); }
}
