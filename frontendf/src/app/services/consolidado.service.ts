import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { ConsolidadoRow } from '../models/consolidado.model';

@Injectable({
  providedIn: 'root'
})
export class ConsolidadoService {
  constructor(private api: ApiService) {}

  getConsolidadoArmado(params?: any): Observable<ConsolidadoRow[]> {
    return this.api.get<ConsolidadoRow[]>('/consolidado/armado/', params);
  }

  createConsolidado(payload: any) {
    return this.api.post<any>('/consolidado/crear/', payload);
  }

  updateConsolidado(id: number, payload: any) {
    return this.api.put<any>(`/consolidado/${id}/`, payload);
  }

  exportarExcel(params?: any) {
    return this.api.getBlob('/consolidado/exportar-excel/', params);
  }

  exportarPdf(params?: any) {
    return this.api.getBlob('/consolidado/exportar-pdf/', params);
  }
}
