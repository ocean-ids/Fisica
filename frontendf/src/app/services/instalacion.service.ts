import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Instalacion } from '../models';

@Injectable({
  providedIn: 'root'
})
export class InstalacionService {
  constructor(private apiService: ApiService){}
  
  getInstalaciones(): Observable<Instalacion[]>{
    return this.apiService.get<Instalacion[]>('/instalaciones/');
  }

  getInstalacion(id: number): Observable<Instalacion>{
    return this.apiService.get<Instalacion>(`/instalaciones/${id}/`);
  }

  CreateInstalacion(instalacion: any): Observable<any>{
    return this.apiService.post<any>('/crear-instalacion/', instalacion);
  }

  updateInstalacion(id: number, instalacion:any): Observable<any>{
    return this.apiService.put<any>(`/actualizar/${id}/`, instalacion);
  }

  deleteInstalacion(id: number): Observable<any>{
    return this.apiService.delete(`/eliminar-instalacion/${id}/`);
  }
  
}
