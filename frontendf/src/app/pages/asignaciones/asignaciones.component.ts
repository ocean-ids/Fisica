import { CommonModule } from '@angular/common';
import { Component, OnInit, ViewChildren, QueryList, AfterViewInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Cliente, Persona, Instalacion, Puesto, Horario, Asignacion } from '../../models';
import { PatronAsignacion } from '../../models/asignacion.model';
import { ClienteService } from '../../services/cliente.service';
import { InstalacionService } from '../../services/instalacion.service';
import { PuestoService } from '../../services/puesto.service';
import { PersonaService } from '../../services/persona.service';
import { HorarioService } from '../../services/horario.service';
import { AsignacionService } from '../../services/asignacion.service';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCardModule } from '@angular/material/card';
import { MatMenuModule } from '@angular/material/menu';
import { AsignacionCalendarioComponent } from '../asignacion-calendario/asignacion-calendario.component';
import { HttpClient } from '@angular/common/http';
import { saveAs } from 'file-saver';
import Swal from 'sweetalert2';
import { PatronAsignacionService } from '../../services/patron-asignacion.service';
import {  MatDialog, MatDialogModule } from '@angular/material/dialog';
import { PatronFormComponent } from '../patrones/patron-form/patron-form.component';
import { PatronSacafrancosModalComponent } from '../patrones/patron-sacafrancos-modal/patron-sacafrancos-modal.component';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { AsignacionFormComponent, AsignacionFormResult } from './asignacion-form/asignacion-form.component';
import { CdkDragDrop, CdkDragMove, DragDropModule, moveItemInArray } from '@angular/cdk/drag-drop';

@Component({
  selector: 'app-asignaciones',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDialogModule,
    MatCardModule,
    MatMenuModule,
    MatButtonModule,
    MatButtonToggleModule,
    DragDropModule,
    AsignacionCalendarioComponent,
    
  ],
  templateUrl: './asignaciones.component.html',
  styleUrl: './asignaciones.component.css'
})
export class AsignacionesComponent implements OnInit {

  @ViewChildren(AsignacionCalendarioComponent)
  calendarios?: QueryList<AsignacionCalendarioComponent>;

  weeksForMonth: string[] = [];
  calendarRowOrder: Array<number | string> = [];
  displayRows: Array<{ type: 'asignacion'; asig: Asignacion; isGroupedChild: boolean } | { type: 'sacafranco'; parent: Asignacion }> = [];
  displayAssignmentRows: Asignacion[] = [];
  hoverSacafrancoParentId: number | null = null;
  draggingAsignacionId: number | null = null;

  private monthStartToday(): string {
    const t = new Date();
    const y = t.getFullYear();
    const m = String(t.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}-01`;
  }

  ngAfterViewInit(): void {
    setTimeout(() => {
        if (this.calendarios && this.calendarios.length) {
          this.calendarios.forEach(c => {
            try { c.weekStartChange.subscribe((ws: string) => {
              if (!ws) return;
              this.dia = ws;
              const parts = ws.split('-');
              if (parts.length === 3) {
                this.anio = Number(parts[0]);
                this.mes = Number(parts[1]);
                this.monthValue = `${this.anio}-${String(this.mes).padStart(2,'0')}`;
              }
              this.cargarAsignaciones();
            }); } catch(e){}
          });

          const ws = this.monthStartToday();
          this.monthValue = `${this.anio}-${String(this.mes).padStart(2,'0')}`;
          this.weeksForMonth = this.computeWeeksForMonth(this.mes, this.anio);
        }
    }, 0);
  }

  getHorasPuesto(puesto: any): string {
    try {
      if (!puesto || !puesto.horarios || !puesto.horarios.length) return '-';
      const entries: number[] = [];
      puesto.horarios.forEach((h: any) => {
        const horasVal = Number(h.horas) || 0;
        const turnoVal = (h.turno || '').toString();
        // usar key para no contar duplicado exacto de horas+turno
        const key = `${horasVal}-${turnoVal}`;
        if (!entries.some((v: any) => v.key === key)) {
          (entries as any).push({ key, horas: horasVal });
        }
      });
      const parts = (entries as any)
        .map((e: any) => e.horas)
        .sort((a: number, b: number) => a - b)
        .map((h: number) => String(h));
      return parts.length ? parts.join(' / ') : '-';
    } catch (e) {
      return '-';
    }
  }

  getTurnosPuesto(puesto: any): string {
    try {
      if (!puesto || !puesto.horarios || !puesto.horarios.length) return '-';
      const ordered = ['Diurno', 'Nocturno', 'Ambos'];
      const unique = new Set<string>();
      puesto.horarios.forEach((h: any) => {
        if (h.turno) unique.add(h.turno);
      });
      const sorted = ordered.filter(t => unique.has(t));
      const extras = [...unique].filter(t => !ordered.includes(t));
      const all = [...sorted, ...extras];
      return all.length ? all.join(', ') : '-';
    } catch (e) {
      return '-';
    }
  }

  getResumenPuestoDisplay(puesto: any): string {
    try {
      if (!puesto || !puesto.horarios || !puesto.horarios.length) return '-';
      const dayMap: any = {1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D'};
      const groups: Record<string, { horas: number; turno: string; dias: number[] }> = {};
      puesto.horarios.forEach((h: any) => {
        const horasVal = Number(h.horas) || 0;
        const turnoVal = h.turno || '';
        const key = `${horasVal}-${turnoVal}`;
        if (!groups[key]) groups[key] = { horas: horasVal, turno: turnoVal, dias: [] };
        if (h.dia && groups[key].dias.indexOf(h.dia) === -1) groups[key].dias.push(h.dia);
      });
      const parts = Object.values(groups)
        .map(g => {
          const diasStr = g.dias.sort((a, b) => a - b).map(d => dayMap[d] || '').join('');
          const base = g.turno ? `${g.horas} ${g.turno}`.trim() : `${g.horas}`;
          return diasStr ? `${base} (${diasStr})` : base;
        })
        .sort();
      return parts.length ? parts.join(' / ') : '-';
    } catch (e) {
      return '-';
    }
  }

  getResumenPuestoCompacto(puesto: any): string {
    try {
      if (!puesto || !puesto.horarios || !puesto.horarios.length) return '-';
      const dayMap: any = {1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D'};
      const groups: Record<string, { horas: number; turno: string; dias: number[] }> = {};
      puesto.horarios.forEach((h: any) => {
        const horasVal = Number(h.horas) || 0;
        const turnoVal = (h.turno || '').toString();
        const key = `${horasVal}-${turnoVal}`;
        if (!groups[key]) groups[key] = { horas: horasVal, turno: turnoVal, dias: [] };
        if (h.dia && groups[key].dias.indexOf(h.dia) === -1) groups[key].dias.push(h.dia);
      });

      const letter = (turno: string): string => {
        const t = turno.toLowerCase();
        if (t.startsWith('d')) return 'D';
        if (t.startsWith('n')) return 'N';
        if (t.startsWith('a')) return 'A';
        return '';
      };

      const parts = Object.values(groups)
        .map(g => {
          const diasStr = g.dias.sort((a: number, b: number) => a - b).map(d => dayMap[d] || '').join('');
          const base = `${g.horas}${letter(g.turno)}`.trim();
          return diasStr ? `${base} ${diasStr}` : base;
        })
        .sort((a, b) => {
          const numA = parseInt(a, 10);
          const numB = parseInt(b, 10);
          return (isNaN(numA) ? 0 : numA) - (isNaN(numB) ? 0 : numB);
        });

      const cant = puesto.cantidad_guardias ? `${puesto.cantidad_guardias}` : '';
      const body = parts.join(' / ');
      if (cant && body) return `${cant} ${body}`;
      if (cant) return `${cant}`;
      return body || '-';
    } catch (e) {
      return '-';
    }
  }

  getCodigoInstalacionAsignacion(asig: any): string {
    if (!asig) return '-';
    return asig.instalacion_detalle?.codigo || asig.instalacionCodigo || '-';
  }

  getDiasPuesto(puesto: any): string {
    try {
      if (!puesto || !puesto.horarios || !puesto.horarios.length) return '-';
      const dayMap: any = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado', 7: 'Domingo'};
      const horarios = puesto.horarios && Array.isArray(puesto.horarios)
        ? puesto.horarios
        : [];
      if (!horarios.length) return '-';

      const groupOrder: string[] = [];
      const groups = new Map<string, Set<number>>();
      for (const h of horarios) {
        const key = `${h.horas ?? ''}-${h.turno ?? ''}`;
        if (!groups.has(key)) {
          groups.set(key, new Set<number>());
          groupOrder.push(key);
        }
        if (h.dia) groups.get(key)!.add(h.dia);
      }

      const parts: string[] = [];
      for (const key of groupOrder) {
        const dias = Array.from(groups.get(key) || []).sort((a: any, b: any) => a - b);
        if (!dias.length) continue;
        const min = dias[0];
        const max = dias[dias.length - 1];
        const start = dayMap[min] || '';
        const end = dayMap[max] || '';
        if (!start || !end) continue;
        parts.push(min === max ? start : `${start} - ${end}`);
      }

      return parts.length ? parts.join(' / ') : '-';
    } catch (e) {
      return '-';
    }
  }

  onSharedDateChange(): void {
    if (!this.dia) {
      this.cargarAsignaciones();
      return;
    }
    // dia formato YYYY-MM-DD
    const parts = this.dia.split('-');
    if (parts.length === 3) {
      this.anio = Number(parts[0]);
      this.mes = Number(parts[1]);
    }
    // sincronizar calendario con la fecha seleccionada
    if (this.calendarios && this.calendarios.length) {
      this.calendarios.forEach(c => {
        c.weekStart = this.dia || '';
        try { c.loadWeek(); } catch(e){}
      });
    }
    this.cargarAsignaciones();
  }

  textoBotonAsignacion: string = 'Guardar';

  asignaciones: Asignacion[] = [];

  mes: number = new Date().getMonth() + 1;
  anio: number = new Date().getFullYear();
  dia: string | null = null; 
  monthValue: string = '';
  filtroTexto: string = '';
  columnasOcultas: string[] = [];

  clientes: Cliente[] = [];
  personas: Persona[] = [];
  horarios: Horario[] = [];
  instalaciones: Instalacion[] = [];
  puestos: Puesto[] = [];
  patrones: PatronAsignacion[] = [];

  clienteSeleccionado: number | null = null;
  instalacionSeleccionada: number | null = null;

  asignacionActual: Asignacion = this.nuevaAsignacion();
  modoEdicion: boolean = false;
  crearCalendarioAutom = true; 

  constructor(
    private clienteService: ClienteService,
    private instalacionService: InstalacionService,
    private puestoService: PuestoService,
    private personaService: PersonaService,
    private horarioService: HorarioService,
    private asignacionService: AsignacionService,
    private http: HttpClient,
    private patronService: PatronAsignacionService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.cargarCatalogos();
    
    this.monthValue = `${this.anio}-${String(this.mes).padStart(2,'0')}`;
    this.cargarAsignaciones();
    // inicializar semanas para el mes actual para que el ngFor tenga datos
    this.weeksForMonth = this.computeWeeksForMonth(this.mes, this.anio);
      console.log('weeksForMonth initialized', this.mes, this.anio, this.weeksForMonth);
  }

  onMonthChange(): void {
    if (!this.monthValue) return;
    const parts = this.monthValue.split('-');
    if (parts.length !== 2) return;
    this.anio = Number(parts[0]);
    this.mes = Number(parts[1]);
    this.dia = null;
    this.filtroTexto = '';
    this.cargarAsignaciones();
    // sincronizar lista de semanas para el mes elegido
    this.weeksForMonth = this.computeWeeksForMonth(this.mes, this.anio);
  }

  onFiltroChange(): void {
    this.cargarAsignaciones();
    if (this.calendarios && this.calendarios.length) {
      this.calendarios.forEach(c => c.loadWeek());
    }
  }

  hideMultipleSelectionIndicator(): boolean {
    return true;
  }

  columnaOculta(key: string): boolean {
    return this.columnasOcultas.includes(key);
  }

  mostrarPuesto(): boolean {
    return !this.columnaOculta('puesto');
  }

  headerRowspan(): number {
    return this.mostrarPuesto() ? 2 : 1;
  }

  totalColumns(): number {
    let count = 0;
    if (!this.columnaOculta('horario')) count += 1;
    if (!this.columnaOculta('codigo')) count += 1;
    if (!this.columnaOculta('cliente')) count += 1;
    if (this.mostrarPuesto()) count += 2;
    if (!this.columnaOculta('cedula')) count += 1;
    if (!this.columnaOculta('persona')) count += 1;
    if (!this.columnaOculta('accion')) count += 1;
    return count || 1;
  }

  private formatDateLocal(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  private computeWeeksForMonth(mes: number, anio: number): string[] {
    const weeksLocal: string[] = [];
    const d = new Date(anio, mes - 1, 1);
    while (d.getMonth() === (mes - 1)) {
      weeksLocal.push(this.formatDateLocal(d));
      d.setDate(d.getDate() + 7);
    }
    return weeksLocal;
  }

  cargarCatalogos(): void {
    this.clienteService.getClientes().subscribe({
      next: data => this.clientes = data,
      error: err => console.error('Error al cargar clientes', err)
    });

    this.personaService.getPersonas().subscribe({
      next: data => this.personas = data,
      error: err => console.error('Error al cargar personas', err)
    });

    this.horarioService.obtenerHorarios().subscribe({
      next: data => this.horarios = data,
      error: err => console.error('Error al cargar horarios', err)
    });
    
    this.patronService.obtenerPatrones().subscribe({
      next: data => this.patrones = data || [],
      error: err => console.error('Error al cargar patrones', err)
    });
  }

  cargarAsignaciones(): void {
    const params: any = {};
    if (this.filtroTexto && this.filtroTexto.trim()) {
      params.q = this.filtroTexto.trim();
    }
    this.asignacionService.obtenerAsignaciones(this.mes, this.anio, params).subscribe({
      next: data => {
        this.asignaciones = data || [];
        this.buildDisplayRows();
        this.updateCalendarOrder();
      },
      error: err => console.error('Error al cargar asignaciones', err)
    });
  }

  dropAsignaciones(event: CdkDragDrop<Asignacion[]>): void {
    if (!event) return;

    const dragged = event.item?.data as Asignacion | undefined;
    if (!dragged) return;
    const draggedId = dragged.id ?? null;

    if (draggedId && this.hoverSacafrancoParentId && this.hoverSacafrancoParentId !== draggedId) {
      if (!this.hasSacafrancoChildren(draggedId)) {
        this.setSacafrancoGroup(dragged, this.hoverSacafrancoParentId);
      }
      return;
    }

    if (event.previousIndex === event.currentIndex) return;
    if (!this.displayAssignmentRows || !this.displayAssignmentRows.length) return;

    moveItemInArray(this.displayAssignmentRows, event.previousIndex, event.currentIndex);
    this.asignaciones = [...this.displayAssignmentRows];
    this.buildDisplayRows();
    this.updateCalendarOrder();
    this.persistOrder();
  }

  trackByAsignacion(index: number, asig: Asignacion): number | string {
    return asig?.id ?? asig?.puesto_detalle?.id ?? index;
  }

  private updateCalendarOrder(): void {
    const source = this.displayAssignmentRows && this.displayAssignmentRows.length
      ? this.displayAssignmentRows
      : (this.asignaciones || []);
    this.calendarRowOrder = source
      .map(asig => asig?.id ?? asig?.puesto_detalle?.id ?? asig?.puesto)
      .filter(v => v !== null && v !== undefined) as Array<number | string>;
  }

  private buildDisplayRows(): void {
    const all = this.asignaciones || [];
    const idSet = new Set<number>();
    all.forEach(a => {
      if (a?.id) idSet.add(a.id);
    });
    const childrenByParent = new Map<number, Asignacion[]>();
    const parentOrder: Asignacion[] = [];

    all.forEach(a => {
      const parentId = a?.sacafranco_grupo ?? null;
      if (parentId && idSet.has(parentId)) {
        if (!childrenByParent.has(parentId)) childrenByParent.set(parentId, []);
        childrenByParent.get(parentId)!.push(a);
      } else {
        parentOrder.push(a);
      }
    });

    const rows: Array<{ type: 'asignacion'; asig: Asignacion; isGroupedChild: boolean } | { type: 'sacafranco'; parent: Asignacion }> = [];
    const displayAssignments: Asignacion[] = [];

    parentOrder.forEach(parent => {
      rows.push({ type: 'asignacion', asig: parent, isGroupedChild: false });
      displayAssignments.push(parent);

      if (parent.agregar_sacafranco) {
        rows.push({ type: 'sacafranco', parent });
      }

      const children = childrenByParent.get(parent.id || -1) || [];
      children.forEach(child => {
        rows.push({ type: 'asignacion', asig: child, isGroupedChild: true });
        displayAssignments.push(child);
      });
    });

    this.displayRows = rows;
    this.displayAssignmentRows = displayAssignments;
  }

  onDragStarted(asig: Asignacion): void {
    this.draggingAsignacionId = asig?.id ?? null;
  }

  onDragEnded(): void {
    this.draggingAsignacionId = null;
    this.hoverSacafrancoParentId = null;
  }

  onDragMoved(event: CdkDragMove): void {
    const point = event?.pointerPosition;
    if (!point) return;
    const el = document.elementFromPoint(point.x, point.y) as HTMLElement | null;
    if (!el) return;
    const row = el.closest('tr[data-sacafranco-parent]') as HTMLElement | null;
    if (!row) {
      this.hoverSacafrancoParentId = null;
      return;
    }
    const raw = row.getAttribute('data-sacafranco-parent');
    const parentId = raw ? Number(raw) : null;
    if (parentId && this.draggingAsignacionId !== null) {
      this.hoverSacafrancoParentId = parentId;
    }
  }

  onSacafrancoHover(parentId?: number): void {
    if (!parentId) return;
    if (this.draggingAsignacionId !== null) {
      this.hoverSacafrancoParentId = parentId;
    }
  }

  onSacafrancoLeave(parentId?: number): void {
    if (!parentId) return;
    if (this.hoverSacafrancoParentId === parentId) {
      this.hoverSacafrancoParentId = null;
    }
  }

  private hasSacafrancoChildren(parentId: number): boolean {
    return (this.asignaciones || []).some(a => a?.sacafranco_grupo === parentId);
  }

  private setSacafrancoGroup(asig: Asignacion, parentId: number | null): void {
    if (!asig || !asig.id) return;
    if ((asig.sacafranco_grupo ?? null) === (parentId ?? null)) return;
    this.asignacionService.actualizarAsignacion(
      asig.id,
      { sacafranco_grupo: parentId } as Partial<Asignacion>
    ).subscribe({
      next: () => {
        asig.sacafranco_grupo = parentId;
        if (parentId) {
          this.moveGroupedAboveChildren(asig, parentId);
        }
        this.buildDisplayRows();
        this.updateCalendarOrder();
        this.persistOrder();
      },
      error: err => console.error('Error al actualizar sacafranco_grupo', err)
    });
  }

  private moveGroupedAboveChildren(asig: Asignacion, parentId: number): void {
    if (!this.asignaciones || !this.asignaciones.length) return;
    const list = [...this.asignaciones];
    const fromIdx = list.findIndex(a => a?.id === asig.id);
    const parentIdx = list.findIndex(a => a?.id === parentId);
    if (fromIdx === -1 || parentIdx === -1) return;

    const [item] = list.splice(fromIdx, 1);
    const insertIdx = parentIdx + 1;
    list.splice(insertIdx, 0, item);
    this.asignaciones = list;
  }

  private persistOrder(): void {
    const source = this.displayAssignmentRows && this.displayAssignmentRows.length
      ? this.displayAssignmentRows
      : (this.asignaciones || []);
    const ordenes = source
      .filter(a => a?.id)
      .map((a, idx) => ({ id: a.id as number, orden: idx }));
    if (!ordenes.length) return;
    this.asignacionService.guardarOrden(ordenes).subscribe({
      next: () => {},
      error: err => console.error('Error al guardar orden', err)
    });
  }

  desagruparAsignacion(asig: Asignacion): void {
    if (!asig?.id || !asig.sacafranco_grupo) return;
    this.setSacafrancoGroup(asig, null);
  }

  trackByDisplayRow(index: number, row: any): string | number {
    if (row?.type === 'sacafranco') return `sacafranco-${row.parent?.id ?? index}`;
    return row?.asig?.id ?? index;
  }

  

 
  prevWeekAndPage(): void {
    if (this.calendarios) this.calendarios.forEach(c => { try { c.prevWeek(); } catch(e){} });
  }

  nextWeekAndPage(): void {
    if (this.calendarios) this.calendarios.forEach(c => { try { c.nextWeek(); } catch(e){} });
  }

  abrirNuevoPatron(): void {
  const ref = this.dialog.open(PatronFormComponent, { width: '480px', data: null });
  ref.afterClosed().subscribe((saved: boolean) => {
    if (saved) {
      
      this.patronService.obtenerPatrones().subscribe({ next: d => this.patrones = d || [] });
    }
  });
}

  nuevaAsignacion(): Asignacion {
    return {
      persona: 0,
      cliente: 0,
      instalacion: 0,
      puesto: 0,
      horario: 0,
      mes: this.mes,
      anio: this.anio,
      estado: 'ACTIVO',
      recurring: true,
      agregar_sacafranco: false,
      sacafranco_grupo: null,
      orden: 0,
      patronAsignacion: 0
    };
  }

  
  onClientChange(): void {
    this.asignacionActual.cliente = this.clienteSeleccionado!;
    this.instalacionSeleccionada = null;
    this.asignacionActual.instalacion = 0;
    this.asignacionActual.puesto = 0;
    this.instalaciones = [];
    this.puestos = [];
    if (this.clienteSeleccionado) {
      this.cargarInstalaciones(this.clienteSeleccionado);
    }
  }

  onInstalacionChange(): void {
    this.asignacionActual.instalacion = this.instalacionSeleccionada!;
    this.asignacionActual.puesto = 0;
    this.puestos = [];
    if (this.instalacionSeleccionada) {
      this.cargarPuestos(this.instalacionSeleccionada);
    }
  }

  private cargarInstalaciones(clienteId: number, preselectInstalacionId?: number, preselectPuestoId?: number): void {
    this.instalacionService.getInstalaciones({ cliente_id: clienteId }).subscribe({
      next: data => {
        this.instalaciones = data || [];
        if (preselectInstalacionId) {
          this.instalacionSeleccionada = preselectInstalacionId;
          this.asignacionActual.instalacion = preselectInstalacionId;
          this.cargarPuestos(preselectInstalacionId, preselectPuestoId);
        }
      },
      error: err => console.error('Error al cargar instalaciones', err)
    });
  }

  private cargarPuestos(instalacionId: number, preselectPuestoId?: number): void {
    this.puestoService.getPuestosPorInstalacion(instalacionId).subscribe({
      next: data => {
        this.puestos = data;
        if (preselectPuestoId) {
          this.asignacionActual.puesto = preselectPuestoId;
        }
      },
      error: err => console.error('Error al cargar puestos', err)
    });
  }


  abrirModalNuevo(): void {
    this.modoEdicion = false;
    this.textoBotonAsignacion = 'Guardar';
    this.asignacionActual = this.nuevaAsignacion();
    this.clienteSeleccionado = null;
    this.instalacionSeleccionada = null;
    this.instalaciones = [];
    this.puestos = [];
    if (this.clientes.length === 0 || this.personas.length === 0 || this.horarios.length === 0) {
      this.cargarCatalogos();
    }
    const ref = this.dialog.open(AsignacionFormComponent, {
      width: '720px',
      data: {
        asignacion: { ...this.asignacionActual },
        modoEdicion: false,
        textoBoton: this.textoBotonAsignacion,
        clientes: this.clientes,
        personas: this.personas,
        horarios: this.horarios,
        patrones: this.patrones,
        clienteSeleccionado: this.clienteSeleccionado,
        instalacionSeleccionada: this.instalacionSeleccionada
      }
    });

    ref.afterClosed().subscribe((result: AsignacionFormResult | undefined) => {
      if (result?.action !== 'save') return;
      if (!result.asignacion) return;
      this.asignacionActual = result.asignacion;
      this.clienteSeleccionado = result.clienteSeleccionado ?? null;
      this.instalacionSeleccionada = result.instalacionSeleccionada ?? null;
      this.modoEdicion = false;
      this.textoBotonAsignacion = 'Guardar';
      this.guardarAsignacion();
    });
  }

  openSacafrancosModal(weekStart: string, day: string, puestoId?: number, manage: boolean = false){
    this.patronService.getSacafrancos(weekStart, day, puestoId).subscribe(list => {
      const ref = this.dialog.open(PatronSacafrancosModalComponent, {
        data: { lista: list, weekStart, day, puestoId, manage },
        width: '480px',
        maxHeight: '70vh',
        panelClass: 'sacafrancos-dialog'
      });
      ref.afterClosed().subscribe(result => {
        if (result?.action === 'assigned' || result?.action === 'unassigned') {
          
          this.cargarAsignaciones();
          if (this.calendarios) this.calendarios.forEach(c => c.loadWeek());
        }
      })
    
    });
}

  descargarReporteExcel() {
  const mm = String(this.mes).padStart(2, '0');
  const url = `http://localhost:8000/api/reporte-asignaciones/?mes=${mm}&anio=${this.anio}`;
  this.http.get(url, { responseType: 'blob' })
    .subscribe({
      next: (blob) => {
        saveAs(blob, `reporte_asignaciones_${this.anio}_${mm}.xlsx`);
      },
      error: err => {
        console.error('Error descargando reporte:', err);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo descargar el reporte' });
      }
    });
  }

  abrirModalEditar(asignacion: Asignacion): void {
    this.modoEdicion = true;
    this.textoBotonAsignacion = 'Actualizar';
    this.asignacionActual = { ...asignacion };

    this.clienteSeleccionado = asignacion.cliente;
    this.instalacionSeleccionada = asignacion.instalacion;

    // cargar catálogos y preseleccionar instalación y puesto del registro
    if (this.clienteSeleccionado) {
      this.cargarInstalaciones(this.clienteSeleccionado, asignacion.instalacion, asignacion.puesto);
    }

    // asegurar horarios/personas disponibles
    if (this.personas.length === 0 || this.horarios.length === 0) {
      this.cargarCatalogos();
    }

    const ref = this.dialog.open(AsignacionFormComponent, {
      width: '720px',
      data: {
        asignacion: { ...this.asignacionActual },
        modoEdicion: true,
        textoBoton: this.textoBotonAsignacion,
        clientes: this.clientes,
        personas: this.personas,
        horarios: this.horarios,
        patrones: this.patrones,
        clienteSeleccionado: this.clienteSeleccionado,
        instalacionSeleccionada: this.instalacionSeleccionada
      }
    });

    ref.afterClosed().subscribe((result: AsignacionFormResult | undefined) => {
      if (result?.action !== 'save') return;
      if (!result.asignacion) return;
      this.asignacionActual = result.asignacion;
      this.clienteSeleccionado = result.clienteSeleccionado ?? null;
      this.instalacionSeleccionada = result.instalacionSeleccionada ?? null;
      this.modoEdicion = true;
      this.textoBotonAsignacion = 'Actualizar';
      this.guardarAsignacion();
    });
  }

  guardarAsignacion(): void {

    if (!this.clienteSeleccionado) {
      Swal.fire({ icon: 'warning', title: 'Falta Cliente', text: 'Debe seleccionar un Cliente' });
      return;
    }
    if (!this.instalacionSeleccionada) {
      Swal.fire({ icon: 'warning', title: 'Falta Instalación', text: 'Debe seleccionar una Instalación' });
      return;
    }
    if (!this.asignacionActual.puesto) {
      Swal.fire({ icon: 'warning', title: 'Falta Puesto', text: 'Debe seleccionar un Puesto' });
      return;
    }
    if (!this.asignacionActual.persona) {
      Swal.fire({ icon: 'warning', title: 'Falta Persona', text: 'Debe seleccionar una Persona' });
      return;
    }
    if (!this.asignacionActual.horario) {
      Swal.fire({ icon: 'warning', title: 'Falta Horario', text: 'Debe seleccionar un Horario' });
      return;
    }

    this.asignacionActual.cliente = this.clienteSeleccionado;
    this.asignacionActual.instalacion = this.instalacionSeleccionada;
    this.asignacionActual.mes = this.mes;
    this.asignacionActual.anio = this.anio;

    const yaExiste = this.asignaciones.some(a =>
      a.persona === this.asignacionActual.persona &&
      a.mes === this.mes &&
      a.anio === this.anio &&
      (!this.modoEdicion || a.id !== this.asignacionActual.id)
    );

    if (yaExiste) {
      Swal.fire({ icon: 'warning', title: 'Duplicado', text: 'Ya existe una asignación para esta persona en este mes.' });
      return;
    }

    // No enviar fecha exacta: las asignaciones se guardan por mes y año
    // (this.asignacionActual as any).fecha = this.dia ? this.dia : null;

    if (this.modoEdicion && this.asignacionActual.id) {
      const payload = { 
        ...this.asignacionActual,
        patronAsignacion: this.asignacionActual.patronAsignacion || null
      } as any;
      this.asignacionService.actualizarAsignacion(
        this.asignacionActual.id,
        payload
      ).subscribe({
        next: () => {
          Swal.fire({ icon: 'success', title: 'Asignación actualizada', timer: 1200, showConfirmButton: false });
          this.cargarAsignaciones();
          this.resetAsignacionState();
          if (this.calendarios) this.calendarios.forEach(c => c.loadWeek());
        },
        error: err => {
          console.error(err);
          Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo actualizar la asignación' });
        }
      });
    } else {
      // Forzar creación de calendario semanal al crear la asignación
      const payload = { ...this.asignacionActual, patronAsignacion: this.asignacionActual.patronAsignacion || null, create_calendar: true } as any;
      this.asignacionService.crearAsignacion(payload).subscribe({
        next: () => {
          Swal.fire({ icon: 'success', title: 'Asignación creada', timer: 1200, showConfirmButton: false });
          this.cargarAsignaciones();
          this.resetAsignacionState();
          if (this.calendarios) this.calendarios.forEach(c => c.loadWeek());
        },
        error: err => {
          console.error(err);
          Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo crear la asignación' });
        }
      });
    }
  }

  private buildRowForPuesto(puestoId: number) {
    const puesto = this.puestos.find(p => p.id === puestoId) as any;
    const weekdayKeys = ['mon','tue','wed','thu','fri','sat','sun'];

    const normalize = (tok: any) => {
      if (!tok && tok !== 0) return '';
      const t = String(tok).trim().toLowerCase();
      const map: any = {
        l: 'lunes', lu: 'lunes', lun: 'lunes', lunes: 'lunes',
        m: 'martes', ma: 'martes', mar: 'martes', martes: 'martes',
        mi: 'miercoles', mie: 'miercoles', miercoles: 'miercoles', 'miércoles':'miercoles',
        j: 'jueves', ju: 'jueves', jue: 'jueves', jueves: 'jueves',
        v: 'viernes', vi: 'viernes', vie: 'viernes', viernes: 'viernes',
        s: 'sabado', sa: 'sabado', sab: 'sabado', sabado: 'sabado', 'sábado':'sabado',
        d: 'domingo', do: 'domingo', dom: 'domingo', domingo: 'domingo'
      };
      return map[t] || t;
    };

    const dayNames = [null,'lunes','martes','miercoles','jueves','viernes','sabado','domingo'];
    const diasNums = (puesto && puesto.horarios) ? Array.from(new Set(puesto.horarios.map((h:any)=>h.dia))) as number[] : [];
    const dias = diasNums.map((n:number)=> dayNames[n]).filter(x=>x);
    const diasNorm = dias.map(normalize).filter((x:any)=>x);
    const turnoRaw = (puesto && puesto.turno) ? String(puesto.turno).trim().toLowerCase() : (puesto && puesto.turno_display ? String(puesto.turno_display).trim().toLowerCase() : '');
    const defaultCode = turnoRaw.startsWith('n') ? 'N' : 'D';

    // Para nueva asignación queremos celdas vacías (el usuario las asigna manualmente)
    const row: any = { puesto: puestoId, puesto_detalle: puesto, mon:'',tue:'',wed:'',thu:'',fri:'',sat:'',sun:'' };
    return row;
  }

  eliminarAsignacion(asignacion: Asignacion): void {
    Swal.fire({
      title: '¿Eliminar asignación?',
      text: `${asignacion.persona_detalle?.apellidos} ${asignacion.persona_detalle?.nombres} (${asignacion.persona_detalle?.tipo})`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    }).then(res => {
      if (!res.isConfirmed || !asignacion.id) return;

      this.asignacionService.eliminarAsignacion(asignacion.id).subscribe({
        next: () => {
          Swal.fire({ icon: 'success', title: 'Asignación eliminada', timer: 1200, showConfirmButton: false });
          this.cargarAsignaciones();
          if (this.calendarios) this.calendarios.forEach(c => c.loadWeek());
        },
        error: err => {
          console.error(err);
          Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo eliminar la asignación' });
        }
      });
    });
  }

  cambiarMesAnio(): void {
    this.cargarAsignaciones();
  }

  private resetAsignacionState(): void {
    this.asignacionActual = this.nuevaAsignacion();
    this.clienteSeleccionado = null;
    this.instalacionSeleccionada = null;
    this.instalaciones = [];
    this.puestos = [];
  }
}
