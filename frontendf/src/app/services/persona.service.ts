import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { from, Observable } from 'rxjs';
import { Persona } from '../models';

@Injectable({
  providedIn: 'root'
})
export class PersonaService {

  constructor(private apiService: ApiService) { }

  getPersonas(params?: { q?: string; tipo?: string; unidad?: string }): Observable<Persona[]>{
    return this.apiService.get<Persona[]>('/personas/', params);
  }

  getPersona(id: number): Observable<Persona>{
    return this.apiService.get<Persona>(`/personas/${id}/`);
  }

  createPersona(persona: Persona): Observable<Persona>{
    return this.apiService.post<Persona>('/crear-persona/', persona);
  }

  updatePersona(id: number, persona: Persona): Observable<Persona>{
    return this.apiService.put<Persona>(`/actualizar-persona/${id}/`, persona);
  }

  deletePersona(id: number): Observable<any>{
    return this.apiService.delete(`/eliminar-persona/${id}/`);
  }

  subirFotoPersona(id: number, file: File): Observable<any> {
    const formData = new FormData();
    formData.append('foto', file);
    return this.apiService.post<any>(`/personas/${id}/foto/`, formData);
  }

  getNomina(id: number): Observable<any> {
    return this.apiService.get<any>(`/personas/${id}/nomina/`);
  }

  guardarNomina(id: number, nomina: any): Observable<any> {
    return this.apiService.put<any>(`/personas/${id}/nomina/guardar/`, nomina);
  }

  getOtrosDatos(id: number): Observable<any> {
    return this.apiService.get<any>(`/personas/${id}/otros-datos/`);
  }

  guardarOtrosDatos(id: number, otros: any): Observable<any> {
    return this.apiService.put<any>(`/personas/${id}/otros-datos/guardar/`, otros);
  }

  getReferencias(id: number): Observable<any> {
    return this.apiService.get<any>(`/personas/${id}/referencias/`);
  }

  guardarReferencias(id: number, ref: any): Observable<any> {
    return this.apiService.put<any>(`/personas/${id}/referencias/guardar/`, ref);
  }

  getDocumentos(id: number): Observable<any[]> {
    return this.apiService.get<any[]>(`/personas/${id}/documentos/`);
  }

  guardarDocumentos(id: number, documentos: any[]): Observable<any> {
    return this.apiService.put<any>(`/personas/${id}/documentos/guardar/`, { documentos });
  }

  getMasReferencias(id: number): Observable<any> {
    return this.apiService.get<any>(`/personas/${id}/mas-referencias/`);
  }

  guardarMasReferencias(id: number, payload: any): Observable<any> {
    return this.apiService.put<any>(`/personas/${id}/mas-referencias/guardar/`, payload);
  }

  getCatalogoCertificados(): Observable<any> {
    return this.apiService.get<any>(`/certificados/catalogo/`);
  }

  getCertificados(id: number): Observable<any> {
    return this.apiService.get<any>(`/personas/${id}/certificados/`);
  }

  guardarCertificados(id: number, marcados: number[]): Observable<any> {
    return this.apiService.put<any>(`/personas/${id}/certificados/guardar/`, { marcados });
  }

  crearTipoCertificado(nombre: string, grupo?: string): Observable<any> {
    return this.apiService.post<any>(`/certificados/tipos/`, { nombre, grupo });
  }

  subirArchivoCertificado(id: number, tipoId: number, file: File): Observable<any> {
    const formData = new FormData();
    formData.append('archivo', file);
    return this.apiService.post<any>(`/personas/${id}/certificados/${tipoId}/archivo/`, formData);
  }

  eliminarArchivoCertificado(id: number, tipoId: number): Observable<any> {
    return this.apiService.delete<any>(`/personas/${id}/certificados/${tipoId}/archivo/eliminar/`);
  }

  disablePersona(id: number): Observable<any>{
    return this.apiService.post(`/disable-persona/${id}/`, {});
  }

  enablePersona(id: number): Observable<any>{
    return this.apiService.post(`/enable-persona/${id}/`, {});
  }

  importPersonas(file: File, dryRun = false) {
    const formData = new FormData();
    formData.append('file', file);
    const endpoint = `/importar-personas/${dryRun ? '?dry_run=true' : ''}`;
    return this.apiService.post<any>(endpoint, formData);
  }

  exportPersonasExcel(params?: { q?: string; tipo?: string; unidad?: string }) {
    return this.apiService.getBlob('/exportar-personas-excel/', params);
  }

}
