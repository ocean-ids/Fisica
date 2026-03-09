import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { ReporteAsistenciaRow, UpdateReporteAsistenciaPayload } from '../models';

@Injectable({
  providedIn: 'root'
})
export class ReporteAsistenciaService {

  constructor(private apiService: ApiService){}

  getReporteAsistencia(params?: any) {
    return this.apiService.get<ReporteAsistenciaRow[]>('/reporte-asistencia/', params);
  }

  updateReporteAsistencia(asignacionId: number, payload: UpdateReporteAsistenciaPayload) {
    return this.apiService.put<ReporteAsistenciaRow>(`/reporte-asistencia/${asignacionId}/`, payload);
  }

  exportarExcel(params?: any) {
    return this.apiService.getBlob('/reporte-asistencia/exportar-excel/', params);
  }

  exportarPdf(params?: any) {
    return this.apiService.getBlob('/reporte-asistencia/exportar-pdf/', params);
  }

}
