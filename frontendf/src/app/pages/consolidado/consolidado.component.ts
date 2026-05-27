import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import Swal from 'sweetalert2';
import { ConsolidadoService } from '../../services/consolidado.service';
import { ConsolidadoRow, ConsolidadoResumenEstado, ConsolidadoResumenManual } from '../../models/consolidado.model';
import { ConsolidadoFormComponent } from './consolidado-form/consolidado-form.component';
import { ConsolidadoEstadoFormComponent } from './consolidado-estado-form/consolidado-estado-form.component';
import { GlobalFilterStateService } from '../../services/global-filter-state.service';
import { Router } from '@angular/router';
import { Subscription, debounceTime, distinctUntilChanged, map } from 'rxjs';
import { PersonaService } from '../../services/persona.service';
import { InstalacionService } from '../../services/instalacion.service';
import { PuestoService } from '../../services/puesto.service';
import { Persona } from '../../models';
import { Puesto } from '../../models/puesto.model';

@Component({
  selector: 'app-consolidado',
  standalone: true,
  imports: [CommonModule, FormsModule, MatButtonToggleModule, MatDialogModule, MatButtonModule, MatIconModule],
  templateUrl: './consolidado.component.html',
  styleUrl: './consolidado.component.css'
})
export class ConsolidadoComponent implements OnInit, OnDestroy {
  lista: ConsolidadoRow[] = [];
  agrupado: { label: string; rows: ConsolidadoRow[] }[] = [];
  filtroFecha = '';
  filtroTurno = '';
  filtroZona = 'Zona 1';
  filtroTexto = '';
  loading = false;
  private filterSub?: Subscription;
  resumenManual: ConsolidadoResumenManual = {
    faltas: 0,
    huecas: 0,
    apoyos: 0,
    capacitacion: 0,
    apertura_puesto: 0,
    servicios_temporales: 0,
    servicios_adicionales: 0,
    aprendiendo_consignas: 0,
    total: 0
  };
  resumenEstado: ConsolidadoResumenEstado = {
    dobla: 0,
    franco_trabajados: 0,
    unidades_eventuales: 0,
    adelanto_turno: 0,
    reten: 0,
    unidades_adicionales: 0,
    custodio: 0,
    total: 0
  };

  constructor(
    private svc: ConsolidadoService,
    private personaSvc: PersonaService,
    private instalacionSvc: InstalacionService,
    private puestoSvc: PuestoService,
    private dialog: MatDialog,
    private globalFilter: GlobalFilterStateService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.setHoy();
    this.filtroTurno = 'Diurno';
    this.cargar();

    this.filterSub = this.globalFilter.state$
      .pipe(
        map(state => {
          if (!this.router.url.startsWith('/dashboard/consolidado')) return null;
          const route = (state?.route || '').toString();
          if (route && !route.startsWith('/dashboard/consolidado')) return null;
          return (state?.query || '').trim();
        }),
        distinctUntilChanged(),
        debounceTime(300)
      )
      .subscribe(query => {
        if (query === null) return;
        this.filtroTexto = query;
        this.cargar(false);
      });
  }

  ngOnDestroy(): void {
    this.filterSub?.unsubscribe();
  }

  onFechaChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.filtroFecha = input.value;
    this.cargar();
  }

  cargar(showLoader: boolean = true): void {
    const params: any = {};
    if (this.filtroTexto) params.q = this.filtroTexto;
    if (this.filtroFecha) params.fecha = this.filtroFecha;
    if (this.filtroTurno) params.turno = this.filtroTurno;
    if (this.filtroZona) params.zona = this.filtroZona;
    if (showLoader) {
      this.loading = true;
    }
    this.svc.getConsolidadoArmado(params).subscribe({
      next: data => {
        this.lista = data || [];
        this.agrupado = this.buildAgrupado();
        if (showLoader) {
          this.loading = false;
        }
      },
      error: err => {
        console.error('Error al cargar consolidado:', err);
        if (showLoader) {
          this.loading = false;
        }
      }
    });
    this.cargarResumen(params);
  }

  private cargarResumen(params: any): void {
    this.svc.getResumen(params).subscribe({
      next: res => {
        if (res?.manual) {
          this.resumenManual = res.manual;
        } else {
          this.resetResumenManual();
        }
        this.resumenEstado = res?.estado_agentes || this.resumenEstado;
        this.resumenManual.total = this.calcManualTotal();
        this.resumenEstado.total = this.calcEstadoTotal();
      },
      error: err => console.error('Error al cargar resumen:', err)
    });
  }

  guardarResumenManual(): void {
    const payload = {
      fecha: this.filtroFecha,
      turno: this.filtroTurno,
      faltas: this.toInt(this.resumenManual.faltas),
      huecas: this.toInt(this.resumenManual.huecas),
      apoyos: this.toInt(this.resumenManual.apoyos),
      capacitacion: this.toInt(this.resumenManual.capacitacion),
      apertura_puesto: this.toInt(this.resumenManual.apertura_puesto),
      servicios_temporales: this.toInt(this.resumenManual.servicios_temporales),
      servicios_adicionales: this.toInt(this.resumenManual.servicios_adicionales),
      aprendiendo_consignas: this.toInt(this.resumenManual.aprendiendo_consignas)
    };

    this.svc.updateResumen(payload).subscribe({
      next: (res: any) => {
        if (res?.manual) {
          this.resumenManual = res.manual;
        }
        this.resumenManual.total = this.calcManualTotal();
        Swal.fire({ icon: 'success', title: 'Resumen guardado', timer: 1200, showConfirmButton: false });
      },
      error: (err) => this.handleActionError(err, 'No se pudo guardar resumen')
    });
  }

  onManualChange(): void {
    this.resumenManual.total = this.calcManualTotal();
  }

  abrirResumenManual(): void {
    const dialogRef = this.dialog.open(ConsolidadoEstadoFormComponent, {
      width: '640px',
      data: { manual: this.resumenManual }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (!result) return;
      this.resumenManual = {
        ...this.resumenManual,
        ...result,
        total: this.calcManualTotal()
      };
      this.guardarResumenManual();
    });
  }

  private buildAgrupado(): { label: string; rows: ConsolidadoRow[] }[] {
    const consola = this.lista.filter(r => r.tipo === 'CONSOLa');
    const guardias = this.lista.filter(r => r.tipo !== 'CONSOLa');

    const zonas: Record<string, ConsolidadoRow[]> = {};
    for (const row of guardias) {
      const zona = (row.zona || '').trim() || 'SIN ZONA';
      if (!zonas[zona]) zonas[zona] = [];
      zonas[zona].push(row);
    }

    const result: { label: string; rows: ConsolidadoRow[] }[] = [];
    if (consola.length) {
      result.push({ label: 'PERSONAL DE CONSOLA Y OFICINAS', rows: consola });
    }

    for (const zona of Object.keys(zonas).sort((a, b) => {
      const diff = this.getZonaOrden(a) - this.getZonaOrden(b);
      return diff !== 0 ? diff : a.localeCompare(b);
    })) {
      result.push({ label: this.getZonaTitulo(zona), rows: zonas[zona] });
    }

    return result;
  }

  private getZonaOrden(zona: string): number {
    const z = (zona || '').trim().toLowerCase();
    if (z === 'zona 1') return 0;
    if (z === 'zona 2') return 1;
    if (z === 'zona 3') return 2;
    return 99;
  }

  private getZonaTitulo(zona: string): string {
    const normalized = (zona || '').trim().toLowerCase();
    if (normalized === 'zona 1') return 'ZONA 1 / DAULE - SAMBORONDON';
    if (normalized === 'zona 2') return 'ZONA 2 / SUR - CENTRO';
    if (normalized === 'zona 3') return 'ZONA 3 / DAULE - NORTE';
    return (zona || '').toUpperCase();
  }

  abrirObservacion(row: ConsolidadoRow): void {
    const dialogRef = this.dialog.open(ConsolidadoFormComponent, {
      width: '640px',
      data: { row }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (!result) return;
      row.observacion = result.observacion || '';
      if (row.tipo === 'CONSOLa') {
        row.nominativo = result.nominativo || '';
        row.proyecto = result.proyecto || '';
        row.puesto = result.puesto || '';
      }
      this.guardarObservacion(row);
    });
  }

  crearPersonalConsola(): void {
    if (!this.filtroFecha || !this.filtroTurno) {
      Swal.fire({ icon: 'warning', title: 'Falta fecha o turno' });
      return;
    }

    this.personaSvc.getPersonas().subscribe({
      next: (personas: Persona[]) => {
        this.instalacionSvc.getInstalaciones({ cliente: 'OCEAN' }).subscribe({
          next: async (instalaciones: any[]) => {
            const candidatos = (personas || []).filter(p => {
              const tipo = (p?.tipo || '').toString().toUpperCase();
              return p?.is_active !== false && (tipo === 'OPERADOR CENTRO CONTROL' || tipo === 'SUPERVISOR CENTRO CONTROL');
            });

            if (!candidatos.length) {
              Swal.fire({ icon: 'info', title: 'Sin personal de consola disponible' });
              return;
            }

            const oceanInstalaciones = (Array.isArray(instalaciones) ? instalaciones : []).filter((inst: any) => {
              const name = (inst?.cliente_nombre || inst?.nombre_cliente || '').toString().toUpperCase();
              return name.includes('OCEAN');
            });

            const personaOptions = candidatos
              .filter(p => p.id)
              .map(p => `<option value="${p.id}">${p.apellidos} ${p.nombres} (${p.tipo || '-'})</option>`)
              .join('');

            const nominativoOptions = oceanInstalaciones
              .map((i: any) => `<option value="${i.codigo || ''}">${i.codigo || '-'}</option>`)
              .join('');

            const proyectoOptions = oceanInstalaciones
              .map((i: any) => `<option value="${i.nombre || ''}">${i.nombre || 'Sin nombre'}</option>`)
              .join('');

            const result = await Swal.fire({
              title: 'Agregar personal de consola',
              html: `
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;text-align:left;">
                  <div style="grid-column:1 / -1;">
                    <label style="font-size:12px;display:block;margin-bottom:4px;">Personal</label>
                    <select id="swal-persona" class="swal2-input" style="margin:0;width:100%;">
                      <option value="">Seleccionar</option>
                      ${personaOptions}
                    </select>
                  </div>
                  <div>
                    <label style="font-size:12px;display:block;margin-bottom:4px;">Nominativo</label>
                    <select id="swal-nominativo" class="swal2-input" style="margin:0;width:100%;">
                      <option value="">Seleccionar</option>
                      ${nominativoOptions}
                    </select>
                  </div>
                  <div>
                    <label style="font-size:12px;display:block;margin-bottom:4px;">Proyecto</label>
                    <select id="swal-proyecto" class="swal2-input" style="margin:0;width:100%;">
                      <option value="">Seleccionar</option>
                      ${proyectoOptions}
                    </select>
                  </div>
                  <div>
                    <label style="font-size:12px;display:block;margin-bottom:4px;">Puesto</label>
                    <select id="swal-puesto" class="swal2-input" style="margin:0;width:100%;">
                      <option value="">Seleccionar</option>
                    </select>
                  </div>
                  <div>
                    <label style="font-size:12px;display:block;margin-bottom:4px;">Observación</label>
                    <textarea id="swal-observacion" class="swal2-textarea" style="margin:0;width:100%;min-height:42px;"></textarea>
                  </div>
                </div>
              `,
              showCancelButton: true,
              confirmButtonText: 'Crear',
              cancelButtonText: 'Cancelar',
              focusConfirm: false,
              didOpen: () => {
                const proyectoEl = document.getElementById('swal-proyecto') as HTMLSelectElement | null;
                const nominativoEl = document.getElementById('swal-nominativo') as HTMLSelectElement | null;
                const puestoEl = document.getElementById('swal-puesto') as HTMLSelectElement | null;

                const applyPuestos = (list: Puesto[]) => {
                  if (!puestoEl) return;
                  puestoEl.innerHTML = '<option value="">Seleccionar</option>' + list.map(p => {
                    const name = (p?.nombre || '-').toString();
                    return `<option value="${name.replace(/"/g, '&quot;')}">${name}</option>`;
                  }).join('');
                };

                const isCompatible = (p: Puesto): boolean => {
                  const turnoActual = (this.filtroTurno || '').toString().trim().toUpperCase();
                  if (!turnoActual) return true;
                  const labels = new Set<string>();
                  const t1 = (p?.turno || '').toString().trim().toUpperCase();
                  const t2 = (p?.turno_display || '').toString().trim().toUpperCase();
                  if (t1) labels.add(t1);
                  if (t2) labels.add(t2);
                  const hs = Array.isArray(p?.horarios) ? p.horarios : [];
                  for (const h of hs) {
                    const t = (h?.turno || '').toString().trim().toUpperCase();
                    if (t) labels.add(t);
                  }
                  const is24h = labels.has('24H') || labels.has('AMBOS');
                  if (is24h) return true;
                  if (turnoActual === 'DIURNO') return labels.has('DIURNO');
                  if (turnoActual === 'NOCTURNO') return labels.has('NOCTURNO');
                  return true;
                };

                const loadByInstalacion = (instId: number) => {
                  this.puestoSvc.getPuestosPorInstalacion(instId).subscribe({
                    next: (rows) => {
                      const puestos = (Array.isArray(rows) ? rows : []).filter(isCompatible);
                      applyPuestos(puestos);
                    },
                    error: () => applyPuestos([])
                  });
                };

                const syncByProyecto = () => {
                  const proyecto = (proyectoEl?.value || '').toString();
                  const match = oceanInstalaciones.find((i: any) => (i?.nombre || '') === proyecto);
                  if (nominativoEl) nominativoEl.value = (match?.codigo || '');
                  if (match?.id) loadByInstalacion(match.id);
                  else applyPuestos([]);
                };

                const syncByNominativo = () => {
                  const codigo = (nominativoEl?.value || '').toString();
                  const match = oceanInstalaciones.find((i: any) => (i?.codigo || '') === codigo);
                  if (proyectoEl) proyectoEl.value = (match?.nombre || '');
                  if (match?.id) loadByInstalacion(match.id);
                  else applyPuestos([]);
                };

                proyectoEl?.addEventListener('change', syncByProyecto);
                nominativoEl?.addEventListener('change', syncByNominativo);
              },
              preConfirm: () => {
                const personaId = Number((document.getElementById('swal-persona') as HTMLSelectElement | null)?.value || 0);
                const nominativo = ((document.getElementById('swal-nominativo') as HTMLSelectElement | null)?.value || '').toString();
                const proyecto = ((document.getElementById('swal-proyecto') as HTMLSelectElement | null)?.value || '').toString();
                const puesto = ((document.getElementById('swal-puesto') as HTMLSelectElement | null)?.value || '').toString();
                const observacion = ((document.getElementById('swal-observacion') as HTMLTextAreaElement | null)?.value || '').toString();

                if (!personaId) {
                  Swal.showValidationMessage('Selecciona una persona');
                  return null;
                }

                return { personaId, nominativo, proyecto, puesto, observacion };
              }
            });

            if (!result.isConfirmed || !result.value) return;

            const personaId = Number(result.value.personaId || 0);
            const repetido = this.lista.some(r => r.tipo === 'CONSOLa' && r.persona_ref_id === personaId);
            if (repetido) {
              Swal.fire({ icon: 'info', title: 'Ese personal ya fue agregado' });
              return;
            }

            this.svc.createConsolidado({
              fecha: this.filtroFecha,
              turno: this.filtroTurno,
              tipo: 'CONSOLa',
              persona_ref_id: personaId,
              nominativo: result.value.nominativo || '',
              proyecto: result.value.proyecto || '',
              puesto: result.value.puesto || '',
              observacion: result.value.observacion || ''
            }).subscribe({
              next: () => {
                Swal.fire({ icon: 'success', title: 'Personal agregado', timer: 1200, showConfirmButton: false });
                this.cargar(false);
              },
              error: (err) => this.handleActionError(err, 'No se pudo agregar')
            });
          },
          error: (err) => this.handleActionError(err, 'No se pudieron cargar instalaciones')
        });
      },
      error: (err) => this.handleActionError(err, 'No se pudo cargar personal')
    });
  }

  eliminarFila(row: ConsolidadoRow): void {
    if (row.tipo !== 'CONSOLa' || !row.consolidado_id) return;

    Swal.fire({
      icon: 'warning',
      title: 'Eliminar personal de consola',
      text: 'Se eliminará este registro del consolidado.',
      showCancelButton: true,
      confirmButtonText: 'Eliminar',
      cancelButtonText: 'Cancelar'
    }).then((res) => {
      if (!res.isConfirmed) return;
      this.svc.deleteConsolidado(row.consolidado_id!).subscribe({
        next: () => {
          Swal.fire({ icon: 'success', title: 'Eliminado', timer: 1000, showConfirmButton: false });
          this.cargar(false);
        },
        error: (err) => this.handleActionError(err, 'No se pudo eliminar')
      });
    });
  }

  private guardarObservacion(row: ConsolidadoRow): void {
    if (!row.tipo) return;
    const personaRefId = row.tipo === 'CONSOLa' ? (row.persona_ref_id ?? null) : null;
    const asignacionRefId = row.tipo === 'GUARDIA' ? (row.asignacion_ref_id ?? null) : null;
    if (row.tipo === 'CONSOLa' && !personaRefId) return;
    if (row.tipo === 'GUARDIA' && !asignacionRefId) return;

    const payload = {
      fecha: row.fecha || this.filtroFecha,
      turno: row.turno || this.filtroTurno,
      tipo: row.tipo,
      persona_ref_id: personaRefId,
      asignacion_ref_id: asignacionRefId,
      nominativo: row.nominativo || '',
      proyecto: row.proyecto || '',
      puesto: row.puesto || '',
      observacion: row.observacion || ''
    };

    if (row.consolidado_id) {
      this.svc.updateConsolidado(row.consolidado_id, {
        observacion: payload.observacion,
        nominativo: payload.nominativo,
        proyecto: payload.proyecto,
        puesto: payload.puesto,
        persona_ref_id: payload.persona_ref_id,
        asignacion_ref_id: payload.asignacion_ref_id
      }).subscribe({
        next: () => {
          Swal.fire({ icon: 'success', title: 'Observacion guardada', timer: 1200, showConfirmButton: false });
        },
        error: (err) => this.handleActionError(err, 'No se pudo guardar')
      });
      return;
    }

    if (!payload.fecha || !payload.turno) {
      Swal.fire({ icon: 'warning', title: 'Falta fecha o turno' });
      return;
    }

    this.svc.createConsolidado(payload).subscribe({
      next: (res: any) => {
        row.consolidado_id = res?.id;
        Swal.fire({ icon: 'success', title: 'Observacion guardada', timer: 1200, showConfirmButton: false });
      },
      error: (err) => this.handleActionError(err, 'No se pudo guardar')
    });
  }

  getNombreCompleto(row: ConsolidadoRow): string {
    const apellidos = (row.apellidos || '').trim();
    const nombres = (row.nombres || '').trim();
    const full = `${apellidos} ${nombres}`.trim();
    return full || '-';
  }

  private calcManualTotal(): number {
    return this.toInt(this.resumenManual.faltas)
      + this.toInt(this.resumenManual.huecas)
      + this.toInt(this.resumenManual.apoyos)
      + this.toInt(this.resumenManual.capacitacion)
      + this.toInt(this.resumenManual.apertura_puesto)
      + this.toInt(this.resumenManual.servicios_temporales)
      + this.toInt(this.resumenManual.servicios_adicionales)
      + this.toInt(this.resumenManual.aprendiendo_consignas);
  }

  private calcEstadoTotal(): number {
    return this.toInt(this.resumenEstado.dobla)
      + this.toInt(this.resumenEstado.franco_trabajados)
      + this.toInt(this.resumenEstado.unidades_eventuales)
      + this.toInt(this.resumenEstado.adelanto_turno)
      + this.toInt(this.resumenEstado.reten)
      + this.toInt(this.resumenEstado.unidades_adicionales)
      + this.toInt(this.resumenEstado.custodio);
  }

  private toInt(value: any): number {
    const num = Number(value);
    return Number.isFinite(num) ? Math.max(0, Math.trunc(num)) : 0;
  }

  private resetResumenManual(): void {
    this.resumenManual = {
      faltas: 0,
      huecas: 0,
      apoyos: 0,
      capacitacion: 0,
      apertura_puesto: 0,
      servicios_temporales: 0,
      servicios_adicionales: 0,
      aprendiendo_consignas: 0,
      total: 0
    };
  }

  descargarExcel(): void {
    const params: any = {};
    if (this.filtroTexto) params.q = this.filtroTexto;
    if (this.filtroFecha) params.fecha = this.filtroFecha;
    if (this.filtroTurno) params.turno = this.filtroTurno;
    if (this.filtroZona) params.zona = this.filtroZona;
    this.svc.exportarExcel(params).subscribe({
      next: (blob: Blob) => this.descargarArchivo(blob, `consolidado_${this.filtroFecha || 'hoy'}.xlsx`),
      error: (err) => this.handleDownloadError(err, 'Excel')
    });
  }

  descargarPdf(): void {
    const params: any = {};
    if (this.filtroTexto) params.q = this.filtroTexto;
    if (this.filtroFecha) params.fecha = this.filtroFecha;
    if (this.filtroTurno) params.turno = this.filtroTurno;
    if (this.filtroZona) params.zona = this.filtroZona;
    this.svc.exportarPdf(params).subscribe({
      next: (blob: Blob) => this.descargarArchivo(blob, `consolidado_${this.filtroFecha || 'hoy'}.pdf`),
      error: (err) => this.handleDownloadError(err, 'PDF')
    });
  }

  private handleDownloadError(err: any, tipo: string): void {
    const status = err?.status;
    const msg = status === 403
      ? 'No autorizado'
      : `No se pudo descargar el ${tipo}`;
    Swal.fire({ icon: 'error', title: 'Error', text: msg });
  }

  private handleActionError(err: any, fallback: string): void {
    const status = err?.status;
    const msg = status === 403 ? 'No autorizado' : fallback;
    Swal.fire({ icon: 'error', title: 'Error', text: msg });
  }

  private descargarArchivo(blob: Blob, nombre: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nombre;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  private setHoy(): void {
    const hoy = new Date();
    const isoLocal = new Date(hoy.getTime() - hoy.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 10);
    this.filtroFecha = isoLocal;
  }
}
