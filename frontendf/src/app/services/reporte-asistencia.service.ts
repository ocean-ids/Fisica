import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { ReporteAsistenciaHistorialItem, ReporteAsistenciaListResponse, ReporteAsistenciaRow, UpdateReporteAsistenciaPayload } from '../models';

@Injectable({
  providedIn: 'root'
})
export class ReporteAsistenciaService {

  constructor(private apiService: ApiService){}

  getReporteAsistencia(params?: any) {
    return this.apiService.get<ReporteAsistenciaListResponse>('/reporte-asistencia/', params);
  }

  updateReporteAsistencia(asignacionId: number, payload: UpdateReporteAsistenciaPayload) {
    return this.apiService.put<ReporteAsistenciaRow>(`/reporte-asistencia/${asignacionId}/`, payload);
  }

  getReporteAsistenciaHistorial(asignacionId: number, params?: any) {
    return this.apiService.get<ReporteAsistenciaHistorialItem[]>(`/reporte-asistencia/${asignacionId}/historial/`, params);
  }

  exportarExcel(params?: any) {
    return this.apiService.getBlob('/reporte-asistencia/exportar-excel/', params);
  }

  exportarPdf(params?: any) {
    return this.apiService.getBlob('/reporte-asistencia/exportar-pdf/', params);
  }

}
