import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Cliente, Persona, Instalacion, Puesto, Horario, Asignacion } from '../../models';
import { PatronAsignacion, SacafrancoFila } from '../../models/asignacion.model';
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
import { AsignacionCalendarioService } from '../../services/asignacion-calendario.service';
import { AsignacionCalendarioRangeModalComponent, AsignacionRangeModalResult } from '../asignacion-calendario/asignacion-calendario-range-modal.component';
import { HttpClient } from '@angular/common/http';
import { saveAs } from 'file-saver';
import Swal from 'sweetalert2';
import { PatronAsignacionService } from '../../services/patron-asignacion.service';
import {  MatDialog, MatDialogModule } from '@angular/material/dialog';
import { PatronFormComponent, PatronFormResult } from '../patrones/patron-form/patron-form.component';
import { PatronSacafrancosModalComponent } from '../patrones/patron-sacafrancos-modal/patron-sacafrancos-modal.component';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { AsignacionFormComponent, AsignacionFormResult } from './asignacion-form/asignacion-form.component';
import { CdkDragDrop, CdkDragMove, DragDropModule, moveItemInArray } from '@angular/cdk/drag-drop';
import { ReporteAsistenciaColorDialogComponent } from '../reporte-asistencia/dialogs/reporte-asistencia-color-dialog.component';
import { Subscription, forkJoin, of } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { GlobalFilterStateService } from '../../services/global-filter-state.service';
import { SacafrancoPersonasModalComponent } from './sacafranco-personas-modal/sacafranco-personas-modal.component';

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
    
    
  ],
  templateUrl: './asignaciones.component.html',
  styleUrl: './asignaciones.component.css'
})
export class AsignacionesComponent implements OnInit, OnDestroy {
  weeksForMonth: string[] = [];
  calendarRowOrder: Array<number | string> = [];
  displayRows: Array<
    { type: 'asignacion'; asig: Asignacion; isGroupedChild: boolean } |
    { type: 'sacafranco'; id: number; fila: SacafrancoFila } |
    { type: 'provincia'; key: string; label: string }
  > = [];
  displayAssignmentRows: Asignacion[] = [];
  sacafrancoRows: SacafrancoFila[] = [];
  calendarDayKeys: string[] = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
  calendarWeekDayKeys: Record<string, string[]> = {};
  calendarData: Record<string, Record<string, any>> = {};
  provinciaSortOrder: Record<string, number> = {};
  draggingAsignacionId: number | null = null;
  private pendingPatronId: number | null = null;
  isSaving = false;

  // Paleta de colores para asignaciones
  readonly colorPalette: {name: string, value: string}[] = [
    { name: 'Amarillo', value: '#fff8b3' },
    { name: 'Rojo', value: '#ffb3b3' },
    { name: 'Verde', value: '#b3ffb3' },
    { name: 'Azul', value: '#b3d9ff' },
    { name: 'Naranja', value: '#ffd9b3' },
    { name: 'Verde Lima', value: '#2ff968' },
    { name: 'Gris', value: '#d9d9d9' },
    { name: 'Celeste', value: '#b3e6ff' },
    { name: 'Rosa', value: '#ffb3e6' },
    { name: 'Beige', value: '#f5f5dc' },
    { name: 'Lima', value: '#d9ffb3' },
    { name: 'Turquesa', value: '#b3fff0' },
    { name: 'Lavanda', value: '#e6b3ff' },
    { name: 'Mostaza', value: '#ffdb58' },
    { name: 'Coral', value: '#ff7f50' },
    { name: 'Cian', value: '#00ffff' },
    { name: 'Crema', value: '#fffdd0' },
    { name: 'Caqui', value: '#f0e68c' },
    { name: 'Salmón', value: '#fa8072' },
    { name: 'Blanco', value: '#ffffff' },
  ];

  // Obtiene las horas de un puesto como un string formateado
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
  // Obtiene los turnos de un puesto como un string formateado
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
      const display = all.map(t => (t === 'Ambos' ? '24H' : t));
      return display.length ? display.join(', ') : '-';
    } catch (e) {
      return '-';
    }
  }

  // Obtiene el resumen de puesto para mostrarlo en la vista, combinando horas, turnos y días de manera legible
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

  // Obtiene un resumen compacto del puesto para mostrarlo en la vista, combinando horas, turnos y días de manera concisa
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
        if (t.startsWith('a')) return 'H';
        return '';
      };

      const parts = Object.values(groups)
        .map(g => {
          const ordered = g.dias.sort((a: number, b: number) => a - b);
          const first = ordered.length ? (dayMap[ordered[0]] || '') : '';
          const last = ordered.length ? (dayMap[ordered[ordered.length - 1]] || '') : '';
          const diasStr = ordered.length <= 1 ? first : `${first}${last}`;
          const base = `${g.horas}${letter(g.turno)}`.trim();
          return diasStr ? `${base} ${diasStr}` : base;
        })
        .sort((a, b) => {
          const numA = parseInt(a, 10);
          const numB = parseInt(b, 10);
          return (isNaN(numA) ? 0 : numA) - (isNaN(numB) ? 0 : numB);
        });

      const cant = puesto.cantidad_puestos ? `${puesto.cantidad_puestos}` : '';
      const body = parts.join(' / ');
      if (cant && body) return `${cant} ${body}`;
      if (cant) return `${cant}`;
      return body || '-';
    } catch (e) {
      return '-';
    }
  }

  // Obtiene el código de la instalación asociada a una asignación, utilizando diferentes campos según la estructura de datos disponible
  getCodigoInstalacionAsignacion(asig: any): string {
    if (!asig) return '-';
    return asig.instalacion_detalle?.codigo || asig.instalacionCodigo || '-';
  }

  // Obtiene los días de un puesto como un string formateado
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

  getDayInitial(dayKey: string): string {
    switch (dayKey) {
      case 'mon': return 'L';
      case 'tue': return 'M';
      case 'wed': return 'X';
      case 'thu': return 'J';
      case 'fri': return 'V';
      case 'sat': return 'S';
      case 'sun': return 'D';
      default: return '';
    }
  }

  getDayNumber(weekStart: string, dayKey: string): string {
    if (!weekStart || !dayKey) return '';
    const parts = weekStart.split('-').map(Number);
    if (parts.length !== 3) return '';
    const base = new Date(parts[0], parts[1] - 1, parts[2]);
    for (let i = 0; i < 7; i += 1) {
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      const key = this.dayKeyFromDate(this.formatDateLocal(d));
      if (key === dayKey) {
        return String(d.getDate());
      }
    }
    return '';
  }

  getCalendarCellClass(value: any): string {
    const raw = (value || '').toString().trim().toUpperCase();
    if (!raw) return '';
    if (raw.startsWith('F')) return 'cell-franco';
    if (raw.startsWith('D')) return 'cell-dia';
    if (raw.startsWith('N')) return 'cell-noche';
    return '';
  }
  
  textoBotonAsignacion: string = 'Guardar';

  asignaciones: Asignacion[] = [];

  mes: number = new Date().getMonth() + 1;
  anio: number = new Date().getFullYear();
  dia: string | null = null; 
  monthValue: string = '';
  filtroTexto: string = '';
  private filterSub?: Subscription;
  columnasOcultas: string[] = [];
  provinciaPage = 1;
  provinciaTotal = 0;
  activeProvinciaId: number | null = null;

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
    private asignacionCalendarioService: AsignacionCalendarioService,
    private http: HttpClient,
    private patronService: PatronAsignacionService,
    private dialog: MatDialog,
    private globalFilter: GlobalFilterStateService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.cargarCatalogos();
    
    this.monthValue = `${this.anio}-${String(this.mes).padStart(2,'0')}`;
    // inicializar semanas para el mes actual para que el ngFor tenga datos
    this.weeksForMonth = this.computeWeeksForMonth(this.mes, this.anio);
    this.buildCalendarWeekDayKeys();
    this.cargarAsignaciones();

    this.filterSub = this.globalFilter.state$.subscribe(state => {
      if (!this.router.url.startsWith('/dashboard/asignaciones')) return;
      this.filtroTexto = state.query || '';
      this.onFiltroChange();  
    });
  }

  ngOnDestroy(): void {
    this.filterSub?.unsubscribe();
  }

  // onMonthChange se encarga de manejar el cambio de mes en el calendario, actualizando el estado del componente y recargando las asignaciones para reflejar el nuevo mes seleccionado
  onMonthChange(): void {
    if (!this.monthValue) return;
    const parts = this.monthValue.split('-');
    if (parts.length !== 2) return;
    this.anio = Number(parts[0]);
    this.mes = Number(parts[1]);
    this.dia = null;
    this.filtroTexto = '';
    this.provinciaPage = 1;
    this.activeProvinciaId = null;
    // sincronizar lista de semanas para el mes elegido
    this.weeksForMonth = this.computeWeeksForMonth(this.mes, this.anio);
    this.buildCalendarWeekDayKeys();
    this.cargarAsignaciones();
    this.loadCalendarWeeks();
  }

  //onFiltroChange se encarga de manejar el cambio en el filtro de texto, recargando las asignaciones para reflejar el nuevo filtro aplicado y actualizando los calendarios para mostrar la información filtrada correctamente
  onFiltroChange(): void {
    this.provinciaPage = 1;
    this.activeProvinciaId = null;
    this.cargarAsignaciones();
    this.loadCalendarWeeks();
  }

  setProvinciaFilter(key: string, label?: string): void {
    const id = this.getProvinciaIdFromKey(key, label);
    if (id == null) return;
    this.activeProvinciaId = id;
    this.provinciaPage = 1;
    this.cargarAsignaciones();
  }

  clearProvinciaFilter(): void {
    if (this.activeProvinciaId == null) return;
    this.activeProvinciaId = null;
    this.provinciaPage = 1;
    this.cargarAsignaciones();
  }

  getTotalPages(): number {
    return this.provinciaTotal || 1;
  }

  prevPage(): void {
    if (this.provinciaPage <= 1) return;
    this.provinciaPage -= 1;
    this.cargarAsignaciones();
  }

  nextPage(): void {
    if (this.provinciaPage >= this.getTotalPages()) return;
    this.provinciaPage += 1;
    this.cargarAsignaciones();
  }

  // hideMultipleSelectionIndicator se utiliza para ocultar el indicador de selección múltiple en la vista, devolviendo siempre true para indicar que no se deben mostrar indicadores adicionales incluso si hay múltiples elementos seleccionados
  hideMultipleSelectionIndicator(): boolean {
    return true;
  }

  // columnaOculta se encarga de verificar si una columna específica está oculta en la vista, comprobando si la clave de la columna se encuentra en el arreglo de columnas ocultas y devolviendo un booleano para indicar su estado
  columnaOculta(key: string): boolean {
    return this.columnasOcultas.includes(key);
  }

  toggleColumna(key: string): void {
    if (this.columnaOculta(key)) {
      this.columnasOcultas = this.columnasOcultas.filter(col => col !== key);
      return;
    }
    this.columnasOcultas = [...this.columnasOcultas, key];
  }

  // mostrarPuesto se encarga de determinar si la columna de puesto debe mostrarse en la vista, verificando si la columna 'puesto' no está oculta y devolviendo un booleano para indicar su visibilidad
  mostrarPuesto(): boolean {
    return !this.columnaOculta('puesto');
  }

  //headerRowspan se utiliza para calcular el valor de rowspan para las celdas del encabezado de la tabla, devolviendo 2 si la columna de puesto se muestra (ya que ocupará dos filas) o 1 si está oculta (ocupando solo una fila), lo que permite ajustar correctamente la estructura del encabezado según las columnas visibles
  headerRowspan(): number {
    return this.mostrarPuesto() ? 2 : 1;
  }

  //abrirColorCedula se encarga de abrir un diálogo para seleccionar el color de la cédula de una asignación específica, permitiendo al usuario elegir un color de una paleta predefinida y luego actualizando la asignación con el color seleccionado a través del servicio correspondiente
  abrirColorCedula(asig: Asignacion): void {
    if (!asig?.id) return;
    const dialogRef = this.dialog.open(ReporteAsistenciaColorDialogComponent, {
      width: '420px',
      maxWidth: '95vw',
      data: {
        selectedColor: asig.cedula_color || this.colorPalette[0].value,
        palette: this.colorPalette
      }
    });

    dialogRef.afterClosed().subscribe((selectedColor?: string) => {
      if (!selectedColor || !asig.id) return;
      this.asignacionService.actualizarAsignacion(asig.id, { cedula_color: selectedColor }).subscribe({
        next: (res) => {
          asig.cedula_color = res.cedula_color || selectedColor;
        },
        error: (err) => console.error('Error al actualizar color de cédula:', err)
      });
    });
  }

  //totalColumns se encarga de calcular el número total de columnas que se deben mostrar en la tabla de asignaciones, teniendo en cuenta las columnas ocultas y si la columna de puesto está visible, para así ajustar dinámicamente el diseño de la tabla según las preferencias del usuario
  totalColumns(): number {
    let count = 0;
    if (!this.columnaOculta('horario')) count += 1;
    if (!this.columnaOculta('codigo')) count += 1;
    count += 1;
    if (!this.columnaOculta('cliente')) count += 1;
    if (this.mostrarPuesto()) count += 2;
    if (!this.columnaOculta('persona')) count += 1;
    if (!this.columnaOculta('accion')) count += 1;
    return count || 1;
  }

  //canDeleteSacafrancoFila se encarga de determinar si una fila de sacafranco puede ser eliminada, verificando si la fila pertenece al mes y año actuales o posteriores, devolviendo un booleano para indicar si se permite la eliminación
  canDeleteSacafrancoFila(fila?: SacafrancoFila | null): boolean {
    return !!fila;
  }
  
  // formatDateLocal se encarga de formatear un objeto Date en un string con formato YYYY-MM-DD, utilizando métodos de la clase Date para obtener el año, mes y día, y asegurándose de que el mes y día tengan dos dígitos mediante el uso de padStart, lo que facilita la manipulación de fechas en el componente
  private formatDateLocal(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  // computeWeeksForMonth se encarga de calcular las fechas de inicio de cada semana para un mes y año específicos, creando un array de strings con formato YYYY-MM-DD que representan el primer día de cada semana dentro del mes, lo que permite mostrar correctamente las semanas en el calendario y sincronizar la vista con las asignaciones correspondientes
  private computeWeeksForMonth(mes: number, anio: number): string[] {
    const weeksLocal: string[] = [];
    const d = new Date(anio, mes - 1, 1);
    while (d.getMonth() === (mes - 1)) {
      weeksLocal.push(this.formatDateLocal(d));
      d.setDate(d.getDate() + 7);
    }
    return weeksLocal;
  }

  private buildCalendarWeekDayKeys(): void {
    const map: Record<string, string[]> = {};
    const dowMap = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    (this.weeksForMonth || []).forEach(ws => {
      const parts = ws.split('-').map(Number);
      if (parts.length !== 3) return;
      const base = new Date(parts[0], parts[1] - 1, parts[2]);
      const keys: string[] = [];
      for (let i = 0; i < 7; i += 1) {
        const d = new Date(base);
        d.setDate(base.getDate() + i);
        keys.push(dowMap[d.getDay()]);
      }
      map[ws] = keys;
    });
    this.calendarWeekDayKeys = map;
  }

  // cargarCatalogos se encarga de cargar los datos necesarios para los catálogos utilizados en el componente, realizando llamadas a los servicios correspondientes para obtener la información de clientes, personas, horarios e instalaciones, y manejando los errores que puedan ocurrir durante la carga de estos datos para asegurar que la vista tenga la información actualizada y disponible para su uso
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

  // cargarAsignaciones se encarga de cargar las asignaciones y filas de sacafranco para el mes y año seleccionados, realizando llamadas a los servicios correspondientes para obtener esta información, aplicando filtros si es necesario, y luego actualizando la vista con los datos obtenidos, además de manejar los errores que puedan ocurrir durante la carga para asegurar que la información mostrada sea precisa y actualizada
  cargarAsignaciones(): void {
    const params: any = {};
    if (this.filtroTexto && this.filtroTexto.trim()) {
      params.q = this.filtroTexto.trim();
    }
    params.lite = true;
    params.provincia_page = this.provinciaPage;

    this.asignacionService
      .obtenerAsignacionesPaginadas(this.mes, this.anio, params)
      .pipe(
        catchError(err => {
          console.error('Error al cargar asignaciones', err);
          return of({
            results: [] as Asignacion[],
            total: 0,
            page: 1,
            size: 0,
            provinciaTotal: 0,
            provinciaPage: this.provinciaPage,
            provinciaId: this.activeProvinciaId
          });
        }),
        switchMap(asignaciones => {
          const provinciaId = asignaciones?.provinciaId ?? null;
          const sacafrancoParams = provinciaId != null ? { provincia_id: provinciaId } : {};
          return this.asignacionService
            .obtenerSacafrancoFilas(this.mes, this.anio, sacafrancoParams)
            .pipe(
              catchError(err => {
                console.error('Error al cargar filas sacafranco', err);
                return of([] as SacafrancoFila[]);
              }),
              switchMap(sacafranco => of({ asignaciones, sacafranco }))
            );
        })
      ).subscribe({
        next: ({ asignaciones, sacafranco }) => {
          this.asignaciones = asignaciones?.results || [];
          this.provinciaTotal = asignaciones?.provinciaTotal ?? this.provinciaTotal;
          this.provinciaPage = asignaciones?.provinciaPage ?? this.provinciaPage;
          this.activeProvinciaId = asignaciones?.provinciaId ?? this.activeProvinciaId;
          this.sacafrancoRows = sacafranco || [];
          this.provinciasDisponibles = this.computeProvinciaOptions();
          this.buildDisplayRows();
          this.updateCalendarOrder();
          this.loadCalendarWeeks();
        },
        error: err => console.error('Error al cargar asignaciones/sacafranco', err)
      });
  }

  private loadCalendarWeeks(): void {
    if (!this.weeksForMonth || !this.weeksForMonth.length) {
      this.calendarData = {};
      return;
    }
    const paramsBase: any = {};
    if (this.filtroTexto && this.filtroTexto.trim()) {
      paramsBase.q = this.filtroTexto.trim();
    }
    const hasSacafranco = (this.sacafrancoRows || []).length > 0;
    const provinciaId = this.activeProvinciaId != null ? this.activeProvinciaId : null;
    this.asignacionCalendarioService.obtenerAsignacionesCalendarioMes(
      this.mes,
      this.anio,
      {
        ...paramsBase,
        lite: true,
        include_sacafranco: hasSacafranco,
        auto_create: true,
        ...(provinciaId != null ? { provincia_id: provinciaId } : {})
      }
    ).subscribe({
      next: res => {
        const weeksMap = res?.weeks || {};
        const map: Record<string, Record<string, any>> = {};
        this.weeksForMonth.forEach(ws => {
          const bucket = weeksMap[ws] || {};
          const asigRows = Array.isArray(bucket?.asignaciones) ? bucket.asignaciones : [];
          const sacRows = Array.isArray(bucket?.sacafranco) ? bucket.sacafranco : [];
          const weekMap: Record<string, any> = {};
          asigRows.forEach((r: any) => {
            const asigKey = String(r?.asignacion ?? r?.asignacion_id ?? '');
            if (asigKey) weekMap[asigKey] = r;
            const puestoKey = String(r?.puesto ?? r?.puesto_id ?? '');
            if (puestoKey && !weekMap[puestoKey]) weekMap[puestoKey] = r;
          });
          sacRows.forEach((r: any) => {
            const filaKey = r?.sacafranco_fila ?? r?.sacafranco_fila_id ?? r?.sacafrancoFila ?? null;
            if (filaKey != null) {
              weekMap[`sacafranco-${filaKey}`] = r;
            }
          });
          map[ws] = weekMap;
        });
        this.calendarData = map;
      },
      error: () => {
        this.calendarData = {};
      }
    });
  }

  private getCalendarRowKey(row: any): string | null {
    if (!row) return null;
    if (row.type === 'sacafranco') return `sacafranco-${row.id}`;
    if (row.type !== 'asignacion') return null;
    return String(row.asig?.id ?? row.asig?.puesto_detalle?.id ?? row.asig?.puesto ?? '');
  }

  getCalendarRow(row: any, weekStart: string): any {
    if (!row || !weekStart) return null;
    const key = this.getCalendarRowKey(row);
    if (!key) return null;
    if (!this.calendarData[weekStart]) this.calendarData[weekStart] = {};
    const weekMap = this.calendarData[weekStart];
    if (!weekMap[key]) {
      weekMap[key] = { mon: '', tue: '', wed: '', thu: '', fri: '', sat: '', sun: '' };
    }
    return weekMap[key];
  }

  onCalendarCellChange(row: any, weekStart: string, dayKey: string, value: any): void {
    if (!row || row.type !== 'asignacion') return;
    const calRow = this.getCalendarRow(row, weekStart);
    if (!calRow) return;
    const v = value ? String(value).toUpperCase().slice(0, 4) : '';
    calRow[dayKey] = v;
    const asignacionId = row.asig?.id ?? null;
    if (!asignacionId) return;
    const payload: any = {
      asignacion_id: asignacionId,
      puesto: row.asig?.puesto ?? row.asig?.puesto_detalle?.id,
      week_start: weekStart,
      mon: calRow.mon || '',
      tue: calRow.tue || '',
      wed: calRow.wed || '',
      thu: calRow.thu || '',
      fri: calRow.fri || '',
      sat: calRow.sat || '',
      sun: calRow.sun || ''
    };
    this.asignacionCalendarioService.crearAsignacionCalendario(payload).subscribe({
      next: () => {},
      error: () => {}
    });
  }

  onSacafrancoCalendarCellChange(row: any, weekStart: string, dayKey: string, value: any): void {
    if (!row || row.type !== 'sacafranco') return;
    const calRow = this.getCalendarRow(row, weekStart);
    if (!calRow) return;
    const v = value ? String(value).toUpperCase().slice(0, 5) : '';
    calRow[dayKey] = v;
    const payload: any = {
      sacafranco_fila: row.id,
      week_start: weekStart
    };
    payload[dayKey] = v;
    this.asignacionCalendarioService.crearSacafrancoFilaSemanal(payload).subscribe({
      next: () => {},
      error: () => {}
    });
  }

  openRangeModal(row: any, weekStart: string, dayKey: string, isSacafranco: boolean): void {
    const clickedDate = this.getDateForDayKey(weekStart, dayKey);
    if (!clickedDate) return;
    const startDefault = this.formatDateLocal(clickedDate);
    const endDefault = this.formatDateLocal(clickedDate);
    const calRow = this.getCalendarRow(row, weekStart);
    const ref = this.dialog.open(AsignacionCalendarioRangeModalComponent, {
      width: '420px',
      data: {
        start: startDefault,
        end: endDefault,
        seq: '',
        isSacafranco,
        weekStart,
        row: calRow
      }
    });

    ref.afterClosed().subscribe((result?: AsignacionRangeModalResult) => {
      if (!result) return;
      const { start, end, seq } = result;
      if (!start || !end || !seq) return;
      const startDate = new Date(start + 'T00:00:00');
      const endDate = new Date(end + 'T00:00:00');
      if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) return;
      const tokens = this.parseSequence(seq, isSacafranco);
      if (!tokens.length) return;
      const anchor = this.parseWeekStart(weekStart);
      const rangeMap = this.buildRangeMap(startDate, endDate, tokens, anchor);
      this.applyRangeToBackend(row, rangeMap, isSacafranco);
      this.applyRangeToCurrentWeek(row, weekStart, rangeMap);
    });
  }

  private parseSequence(seq: string, isSacafranco: boolean): string[] {
    const raw = (seq || '').trim().toUpperCase();
    if (!raw) return [];
    if (!isSacafranco) {
      const letters = raw.match(/[FDN]/g) || [];
      return letters;
    }
    const parts = raw.split(/[,\s]+/).filter(Boolean);
    return parts.length ? parts : [raw];
  }

  private buildRangeMap(startDate: Date, endDate: Date, tokens: string[], anchorWeekStart?: Date | null): Record<string, Record<string, string>> {
    const map: Record<string, Record<string, string>> = {};
    let idx = 0;
    const d = new Date(startDate);
    const anchorStart = anchorWeekStart ? new Date(anchorWeekStart) : null;
    const anchorEnd = anchorStart ? new Date(anchorStart) : null;
    if (anchorEnd) anchorEnd.setDate(anchorEnd.getDate() + 6);
    while (d <= endDate) {
      const weekStart = (anchorStart && anchorEnd && d >= anchorStart && d <= anchorEnd)
        ? anchorStart
        : this.getWeekStartForDate(d);
      const weekKey = this.formatDateLocal(weekStart);
      const dayKey = this.dayKeyFromDate(this.formatDateLocal(d));
      if (!map[weekKey]) map[weekKey] = {};
      map[weekKey][dayKey] = tokens[idx % tokens.length];
      idx += 1;
      d.setDate(d.getDate() + 1);
    }
    return map;
  }

  private parseWeekStart(weekStartStr: string): Date | null {
    if (!weekStartStr) return null;
    const parts = weekStartStr.split('-').map(Number);
    if (parts.length !== 3) return null;
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }

  private getWeekStartForDate(d: Date): Date {
    const y = d.getFullYear();
    const m = d.getMonth();
    const day = d.getDate();
    const startDay = 1 + Math.floor((day - 1) / 7) * 7;
    return new Date(y, m, startDay);
  }

  private getDateForDayKey(weekStartStr: string, dayKey: string): Date | null {
    if (!weekStartStr || !dayKey) return null;
    const parts = weekStartStr.split('-').map(Number);
    if (parts.length !== 3) return null;
    const base = new Date(parts[0], parts[1] - 1, parts[2]);
    for (let i = 0; i < 7; i += 1) {
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      if (this.dayKeyFromDate(this.formatDateLocal(d)) === dayKey) return d;
    }
    return null;
  }

  private dayKeyFromDate(dateStr: string): string {
    if (!dateStr) return '';
    const parts = dateStr.split('-').map(Number);
    if (parts.length !== 3) return '';
    const d = new Date(parts[0], parts[1] - 1, parts[2]);
    const map = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    return map[d.getDay()];
  }

  private applyRangeToBackend(row: any, rangeMap: Record<string, Record<string, string>>, isSacafranco: boolean): void {
    const requests: any[] = [];
    Object.keys(rangeMap).forEach(weekStart => {
      const days = rangeMap[weekStart] || {};
      if (!Object.keys(days).length) return;
      if (isSacafranco) {
        const filaId = row?.id;
        if (!filaId) return;
        const payload: any = { sacafranco_fila: filaId, week_start: weekStart };
        Object.keys(days).forEach(k => payload[k] = days[k]);
        requests.push(this.asignacionCalendarioService.crearSacafrancoFilaSemanal(payload));
      } else {
        const asignacionId = row?.asig?.id;
        if (!asignacionId) return;
        const payload: any = {
          asignacion_id: asignacionId,
          puesto: row.asig?.puesto ?? row.asig?.puesto_detalle?.id,
          week_start: weekStart
        };
        Object.keys(days).forEach(k => payload[k] = days[k]);
        requests.push(this.asignacionCalendarioService.crearAsignacionCalendario(payload));
      }
    });
    if (!requests.length) return;
    forkJoin(requests).subscribe({ next: () => {}, error: () => {} });
  }

  private applyRangeToCurrentWeek(row: any, weekStart: string, rangeMap: Record<string, Record<string, string>>): void {
    const weekDays = rangeMap[weekStart] || {};
    const calRow = this.getCalendarRow(row, weekStart);
    if (!calRow) return;
    Object.keys(weekDays).forEach(k => {
      calRow[k] = weekDays[k];
    });
  }

  //crearSacafrancoFila crea una fila de sacafranco vacía para el mes y año seleccionados
  crearSacafrancoFila(): void {
    const ref = this.dialog.open(SacafrancoPersonasModalComponent, {
      width: '520px',
      maxHeight: '70vh',
      data: {
        assignedPersonaIds: this.getAssignedSacafrancoPersonaIds(),
        provincias: this.provinciasDisponibles,
        provinciaId: null
      }
    });

    ref.afterClosed().subscribe(result => {
      if (!result?.personaId) return;
      const payload: SacafrancoFila = {
        mes: this.mes,
        anio: this.anio,
        orden: (this.sacafrancoRows || []).length,
        persona: result.personaId,
        provincia: result.provinciaId ?? null
      };

      this.asignacionService.crearSacafrancoFila(payload).subscribe({
        next: fila => {
          this.sacafrancoRows = [...(this.sacafrancoRows || []), fila].filter(f => f && f.id);
          this.buildDisplayRows();
          this.updateCalendarOrder();
          this.loadCalendarWeeks();
        },
        error: err => console.error('Error al crear fila sacafranco', err)
      });
    });
  }

  provinciasDisponibles: Array<{ id: number; nombre: string }> = [];

  private computeProvinciaOptions(): Array<{ id: number; nombre: string }> {
    const map = new Map<number, string>();
    (this.asignaciones || []).forEach(asig => {
      const id = asig?.instalacion_detalle?.provincia_id;
      const nombre = (asig?.instalacion_detalle?.provincia_nombre || '').trim();
      if (!id || !nombre) return;
      if (!map.has(id)) map.set(id, nombre);
    });
    (this.sacafrancoRows || []).forEach(fila => {
      const id = fila?.provincia ?? null;
      const nombre = (fila?.provincia_nombre || '').trim();
      if (!id || !nombre) return;
      if (!map.has(id)) map.set(id, nombre);
    });
    return Array.from(map.entries())
      .map(([id, nombre]) => ({ id, nombre }))
      .sort((a, b) => a.nombre.localeCompare(b.nombre));
  }

  private getAssignedSacafrancoPersonaIds(): number[] {
    return (this.sacafrancoRows || [])
      .map(r => r?.persona || r?.persona_detalle?.id)
      .filter((id): id is number => !!id);
  }

  private buildProvinciaSortOrderFromRows(rows: Array<any>): void {
    const order: Record<string, number> = {};
    let idx = 0;
    rows.forEach(row => {
      if (row?.type !== 'provincia') return;
      const key = row.key || 'provincia-none';
      if (order[key] == null) {
        order[key] = idx;
        idx += 1;
      }
    });
    this.provinciaSortOrder = order;
  }

  //editarSacafrancoFila queda sin lógica de selección de persona
  editarSacafrancoFila(_fila: SacafrancoFila): void {
    return;
  }

  //eliminarSacafrancoFila se encarga de eliminar una fila de sacafranco específica, mostrando una confirmación al usuario antes de realizar la eliminación, y luego actualizando la vista para reflejar la eliminación de la fila, además de manejar los errores que puedan ocurrir durante el proceso para asegurar que la operación se realice correctamente
  eliminarSacafrancoFila(fila: SacafrancoFila | number | null | undefined): void {
    const id = typeof fila === 'number' ? fila : fila?.id;
    if (!id) return;
    Swal.fire({
      title: 'Eliminar fila sacafranco',
      text: 'Esta accion no se puede deshacer. Deseas continuar?',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Si, eliminar',
      cancelButtonText: 'Cancelar'
    }).then(result => {
      if (!result.isConfirmed) return;
      this.asignacionService.eliminarSacafrancoFila(id).subscribe({
        next: () => {
          this.sacafrancoRows = (this.sacafrancoRows || []).filter(f => f?.id !== id);
          this.buildDisplayRows();
          this.updateCalendarOrder();
          this.persistSacafrancoOrder();
          this.persistOrder();
        },
        error: err => console.error('Error al eliminar fila sacafranco', err)
      });
    });
  }

  //dropAsignaciones se encarga de manejar el evento de arrastrar y soltar para reordenar las asignaciones y filas de sacafranco en la vista, actualizando el orden de los elementos en el arreglo de visualización, recalculando el orden para cada elemento, y luego persistiendo los cambios en el backend a través de llamadas a los servicios correspondientes, además de manejar los errores que puedan ocurrir durante el proceso para asegurar que la operación se realice correctamente
  dropAsignaciones(event: CdkDragDrop<any[]>): void {
    if (!event) return;

    const draggedRow = event.item?.data as any;
    if (!draggedRow) return;
    const dragged = draggedRow.type === 'asignacion' ? draggedRow.asig as Asignacion : null;
    const draggedId = dragged?.id ?? null;

    if (event.previousIndex === event.currentIndex) return;
    if (!this.displayRows || !this.displayRows.length) return;

    const getHeaderKeyAbove = (rows: any[], index: number): string | null => {
      if (rows[index]?.type === 'provincia') return rows[index].key || null;
      for (let i = index; i >= 0; i -= 1) {
        const row = rows[i];
        if (row?.type === 'provincia') return row.key || null;
      }
      return null;
    };

    const getRowProvinciaKey = (row: any): string | null => {
      if (!row) return null;
      if (row.type === 'provincia') return row.key || null;
      if (row.type === 'asignacion') return this.getProvinciaKeyFromAsignacion(row.asig);
      if (row.type === 'sacafranco') return this.getProvinciaKeyFromSacafranco(row.fila);
      return null;
    };

    const sourceKey = getRowProvinciaKey(draggedRow) || getHeaderKeyAbove(this.displayRows || [], event.previousIndex);
    const orderableRows = (this.displayRows || []).filter(r => r?.type === 'asignacion' || r?.type === 'sacafranco');
    const targetRowPre = orderableRows[event.currentIndex] || null;
    const targetKey = getRowProvinciaKey(targetRowPre);
    if (!sourceKey || !targetKey || sourceKey !== targetKey) {
      return;
    }

    moveItemInArray(orderableRows, event.previousIndex, event.currentIndex);

    const rebuiltRows: Array<any> = [];
    let lastKey: string | null = null;
    orderableRows.forEach(row => {
      const key = getRowProvinciaKey(row) || 'provincia-none';
      if (key !== lastKey) {
        const label = row.type === 'asignacion'
          ? this.getProvinciaLabel(row.asig)
          : this.getSacafrancoProvinciaLabel(row.fila);
        rebuiltRows.push({ type: 'provincia', key, label });
        lastKey = key;
      }
      rebuiltRows.push(row);
    });
    this.displayRows = rebuiltRows as any;

    this.buildProvinciaSortOrderFromRows(this.displayRows || []);


    const ordenAsignaciones: { id: number; orden: number }[] = [];
    const ordenSacafranco: { id: number; orden: number }[] = [];

    const provinceKey = sourceKey;
    const blockRows = orderableRows.filter(r => {
      if (!r || (r.type !== 'asignacion' && r.type !== 'sacafranco')) return false;
      return (getRowProvinciaKey(r) || '') === provinceKey;
    });

    // Reasignar orden solo dentro del bloque de la provincia
    blockRows.forEach((row, idx) => {
      if (row.type === 'asignacion' && row.asig?.id) {
        row.asig.orden = idx;
        ordenAsignaciones.push({ id: row.asig.id, orden: idx });
      }
      if (row.type === 'sacafranco' && row.fila?.id) {
        row.fila.orden = idx;
        ordenSacafranco.push({ id: row.fila.id, orden: idx });
      }
    });

    this.displayAssignmentRows = (this.displayRows || [])
      .filter(r => r?.type === 'asignacion')
      .map(r => r.asig)
      .filter(a => !!a);
    this.asignaciones = [...this.displayAssignmentRows];

    this.sacafrancoRows = (this.displayRows || [])
      .filter(r => r?.type === 'sacafranco')
      .map(r => r.fila)
      .filter(f => !!f);

    this.updateCalendarOrder();
    this.persistOrder(ordenAsignaciones);
    this.persistSacafrancoOrder(ordenSacafranco);
  }

  // trackByAsignacion se utiliza como función de seguimiento para optimizar la renderización de la lista de asignaciones en la vista, devolviendo un identificador único para cada asignación basado en su id, el id del puesto detalle o el índice como último recurso, lo que permite a Angular identificar correctamente los elementos y evitar renderizaciones innecesarias al actualizar la lista
  trackByAsignacion(index: number, asig: Asignacion): number | string {
    return asig?.id ?? asig?.puesto_detalle?.id ?? index;
  }

  // UpdateCalendarOrder se encarga de actualizar el orden de las filas en el calendario según el orden actual de las filas de asignaciones y sacafranco en la vista, generando un nuevo arreglo de orden basado en los identificadores de las asignaciones y filas, y luego actualizando la propiedad que controla el orden en el calendario para reflejar los cambios realizados por el usuario
  private updateCalendarOrder(): void {
    if (this.displayRows && this.displayRows.length) {
      this.calendarRowOrder = this.displayRows
        .map(row => {
          if ((row as any).type === 'provincia') {
            return `provincia-${(row as any).label ?? ''}`;
          }
          if ((row as any).type === 'sacafranco') {
            return `sacafranco-${(row as any).id}`;
          }
          return (row as any).asig?.id ?? (row as any).asig?.puesto_detalle?.id ?? (row as any).asig?.puesto;
        })
        .filter(v => v !== null && v !== undefined) as Array<number | string>;
      return;
    }
    this.calendarRowOrder = [];
  }

  // buildDisplayRows se encarga de construir el arreglo de filas que se mostrarán en la vista combinando las asignaciones y filas de sacafranco, ordenándolas según su propiedad de orden, y luego actualizando las propiedades que controlan la visualización de las filas en la tabla y el calendario, lo que permite mostrar la información de manera organizada y coherente para el usuario
  private buildDisplayRows(): void {
    const asignaciones = (this.asignaciones || [])
      .filter(a => a?.persona_detalle?.is_active !== false);
    const sacRows = this.sacafrancoRows || [];
    const previousRows = this.displayRows || [];
    if (!Object.keys(this.provinciaSortOrder || {}).length && previousRows.length) {
      this.buildProvinciaSortOrderFromRows(previousRows);
    }

    const rows: Array<
      { type: 'asignacion'; asig: Asignacion; isGroupedChild: boolean } |
      { type: 'sacafranco'; id: number; fila: SacafrancoFila } |
      { type: 'provincia'; key: string; label: string }
    > = [];
    const displayAssignments: Asignacion[] = [];

    const orderables: Array<{ kind: 'asignacion'; asig: Asignacion } | { kind: 'sacafranco'; fila: SacafrancoFila }> = [
      ...asignaciones.map(a => ({ kind: 'asignacion' as const, asig: a })),
      ...sacRows.map(f => ({ kind: 'sacafranco' as const, fila: f }))
    ];

    let lastProvincia: string | null = null;

    orderables
      .sort((a, b) => {
        const aKey = a.kind === 'asignacion'
          ? this.getProvinciaKeyFromAsignacion(a.asig)
          : this.getProvinciaKeyFromSacafranco(a.fila);
        const bKey = b.kind === 'asignacion'
          ? this.getProvinciaKeyFromAsignacion(b.asig)
          : this.getProvinciaKeyFromSacafranco(b.fila);
        const aGroup = this.provinciaSortOrder[aKey] ?? 0;
        const bGroup = this.provinciaSortOrder[bKey] ?? 0;
        if (aGroup !== bGroup) return aGroup - bGroup;
        const aOrd = a.kind === 'asignacion' ? (a.asig.orden ?? 0) : (a.fila.orden ?? 0);
        const bOrd = b.kind === 'asignacion' ? (b.asig.orden ?? 0) : (b.fila.orden ?? 0);
        return aOrd - bOrd;
      })
      .forEach(item => {
        if (item.kind === 'asignacion') {
          const provinciaKey = this.getProvinciaKeyFromAsignacion(item.asig);
          const provinciaLabel = this.getProvinciaLabel(item.asig);
          if (provinciaKey !== lastProvincia) {
            rows.push({ type: 'provincia', key: provinciaKey, label: provinciaLabel });
            lastProvincia = provinciaKey;
          }
          rows.push({ type: 'asignacion', asig: item.asig, isGroupedChild: false });
          displayAssignments.push(item.asig);
          return;
        }
        const sacProvinciaKey = this.getProvinciaKeyFromSacafranco(item.fila);
        const sacProvinciaLabel = this.getSacafrancoProvinciaLabel(item.fila);
        if (sacProvinciaKey !== lastProvincia) {
          rows.push({ type: 'provincia', key: sacProvinciaKey, label: sacProvinciaLabel });
          lastProvincia = sacProvinciaKey;
        }
        rows.push({ type: 'sacafranco', id: item.fila.id as number, fila: item.fila });
      });

    this.displayRows = rows;
    this.displayAssignmentRows = displayAssignments;
  }

  //onDragStarted se encarga de manejar el evento de inicio de arrastre para una asignación específica, actualizando el estado del componente para indicar qué asignación está siendo arrastrada, lo que permite controlar la lógica relacionada con el arrastre y soltar en la vista, como mostrar indicadores visuales o habilitar ciertas funcionalidades mientras se realiza el arrastre
  onDragStarted(asig: Asignacion): void {
    this.draggingAsignacionId = asig?.id ?? null;
  }

  // onDragEnded se encarga de manejar el evento de finalización de arrastre para una asignación, restableciendo el estado del componente para indicar que ya no se está arrastrando ninguna asignación, y luego utilizando un temporizador para limpiar cualquier punto de referencia relacionado con el arrastre después de un breve retraso, lo que ayuda a evitar problemas de renderización o lógica relacionada con el arrastre en la vista
  onDragEnded(): void {
    this.draggingAsignacionId = null;
  }

  //persistOrder se encarga de persistir el orden de las asignaciones en el backend, tomando un arreglo opcional de ordenes que contiene los identificadores y el nuevo orden de las asignaciones, y luego realizando una llamada al servicio correspondiente para guardar esta información, además de manejar los errores que puedan ocurrir durante el proceso para asegurar que la operación se realice correctamente
  private persistOrder(ordenes?: { id: number; orden: number }[]): void {
    const payload = (ordenes && ordenes.length)
      ? ordenes
      : this.computeCombinedOrders().ordenAsignaciones;
    if (!payload.length) return;
    this.asignacionService.guardarOrden(payload).subscribe({
      next: () => {},
      error: err => console.error('Error al guardar orden', err)
    });
  }

  //persistSacafrancoOrder se encarga de persistir el orden de las filas de sacafranco en el backend, tomando un arreglo opcional de ordenes que contiene los identificadores y el nuevo orden de las filas, y luego realizando una llamada al servicio correspondiente para guardar esta información, además de manejar los errores que puedan ocurrir durante el proceso para asegurar que la operación se realice correctamente
  private persistSacafrancoOrder(ordenes?: { id: number; orden: number }[]): void {
    const payload = (ordenes && ordenes.length)
      ? ordenes
      : this.computeCombinedOrders().ordenSacafranco;
    if (!payload.length) return;
    this.asignacionService.guardarOrdenSacafranco(payload).subscribe({
      next: () => {},
      error: err => console.error('Error al guardar orden sacafranco', err)
    });
  }

  private computeCombinedOrders(): { ordenAsignaciones: { id: number; orden: number }[]; ordenSacafranco: { id: number; orden: number }[] } {
    const ordenAsignaciones: { id: number; orden: number }[] = [];
    const ordenSacafranco: { id: number; orden: number }[] = [];
    const orderableRows = (this.displayRows || []).filter(r =>
      r?.type === 'sacafranco' || r?.type === 'asignacion'
    );
    orderableRows.forEach((row, idx) => {
      if (row.type === 'asignacion' && row.asig?.id) {
        ordenAsignaciones.push({ id: row.asig.id, orden: idx });
      }
      if (row.type === 'sacafranco' && row.fila?.id) {
        ordenSacafranco.push({ id: row.fila.id, orden: idx });
      }
    });
    return { ordenAsignaciones, ordenSacafranco };
  }

  //trackByDisplayRow se encarga de proporcionar una función de seguimiento para las filas de la vista, utilizando el identificador único de cada fila o su índice como clave, lo que ayuda a Angular a optimizar la renderización de la lista y mejorar el rendimiento
  trackByDisplayRow(index: number, row: any): string | number {
    if (row?.type === 'sacafranco') return `sacafranco-${row.id ?? index}`;
    if (row?.type === 'provincia') return `provincia-${row.key ?? index}`;
    return row?.asig?.id ?? index;
  }

  private getProvinciaLabel(asig: Asignacion): string {
    const label = (asig?.instalacion_detalle?.provincia_nombre || '').trim();
    return label || 'SIN PROVINCIA';
  }

  private getSacafrancoProvinciaLabel(fila: SacafrancoFila): string {
    const label = (fila?.provincia_nombre || '').trim();
    if (label) return label;
    const id = (fila?.provincia ?? fila?.persona_detalle?.provincia) ?? null;
    if (id == null) return 'SIN PROVINCIA';
    const fromList = (this.provinciasDisponibles || []).find(p => p.id === id)?.nombre || '';
    return fromList.trim() || 'SIN PROVINCIA';
  }

  private getProvinciaKeyFromAsignacion(asig: Asignacion): string {
    const id = asig?.instalacion_detalle?.provincia_id ?? null;
    if (id != null) return `provincia-${id}`;
    const label = this.getProvinciaLabel(asig);
    return label ? `provincia-label-${label}` : 'provincia-none';
  }

  private getProvinciaKeyFromSacafranco(fila: SacafrancoFila): string {
    const id = (fila?.provincia ?? fila?.persona_detalle?.provincia) ?? null;
    if (id != null) return `provincia-${id}`;
    const label = this.getSacafrancoProvinciaLabel(fila);
    return label ? `provincia-label-${label}` : 'provincia-none';
  }

  private getProvinciaIdMap(): Record<string, number> {
    const map: Record<string, number> = {};
    (this.provinciasDisponibles || []).forEach(p => {
      const label = (p?.nombre || '').trim();
      if (!label || p?.id == null) return;
      if (map[label] == null) map[label] = p.id;
    });
    (this.sacafrancoRows || []).forEach(fila => {
      const label = (fila?.provincia_nombre || '').trim();
      const id = fila?.provincia ?? null;
      if (!label || id == null) return;
      if (map[label] == null) map[label] = id;
    });
    (this.asignaciones || []).forEach(asig => {
      const label = (asig?.instalacion_detalle?.provincia_nombre || '').trim();
      const id = asig?.instalacion_detalle?.provincia_id;
      if (!label || id == null) return;
      if (map[label] == null) map[label] = id;
    });
    return map;
  }

  private getProvinciaIdFromKey(key: string, label?: string): number | null {
    if (!key) return null;
    if (key.startsWith('provincia-')) {
      const raw = key.replace('provincia-', '').trim();
      const id = Number(raw);
      return Number.isFinite(id) ? id : null;
    }
    const map = this.getProvinciaIdMap();
    const labelKey = (label || '').trim();
    if (labelKey && map[labelKey] != null) return map[labelKey];
    const fallback = key.replace('provincia-label-', '').trim();
    return map[fallback] ?? null;
  }

  //abrirNuevoPatron se encarga de abrir un diálogo para crear un nuevo patrón de asignación, permitiendo al usuario ingresar la información necesaria para el patrón, y luego actualizando la vista con el nuevo patrón creado, además de manejar los errores que puedan ocurrir durante el proceso para asegurar que la operación se realice correctamente
  abrirNuevoPatron(): void {
    const ref = this.dialog.open(PatronFormComponent, {
      width: '480px',
      data: { patron: null }
    });
    ref.afterClosed().subscribe((result?: PatronFormResult) => {
      if (!result?.saved || !result.patron) return;
      const exists = this.patrones.find(p => p.id === result.patron?.id);
      if (!exists) {
        this.patrones = [...this.patrones, result.patron];
      }
      this.pendingPatronId = result.patron.id || null;
      this.asignacionActual.patronAsignacion = result.patron.id;
      this.asignacionActual.end_date = null;
      this.asignacionActual.recurring = true;
    });
  }

  //nuevaAsignacion se encarga de crear una nueva instancia de asignación con valores predeterminados, incluyendo información sobre la persona, cliente, instalación, puesto, horario, mes, año, estado, recurrencia, fechas de inicio y fin, y patrón de asignación pendiente
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
      start_date: `${this.anio}-${String(this.mes).padStart(2, '0')}-01`,
      end_date: null,
      agregar_sacafranco: false,
      sacafranco_grupo: null,
      orden: 0,
      patronAsignacion: this.pendingPatronId || 0
    };
  }

  //onClientChange se encarga de manejar el cambio en la selección del cliente para una asignación, actualizando el estado de la asignación actual con el nuevo cliente seleccionado, restableciendo las selecciones de instalación y puesto, y luego cargando las instalaciones correspondientes al nuevo cliente seleccionado para actualizar la vista con la información relevante
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

  //onInstalacionChange se encarga de manejar el cambio en la selección de la instalación para una asignación, actualizando el estado de la asignación actual con la nueva instalación seleccionada, restableciendo la selección de puesto, y luego cargando los puestos correspondientes a la nueva instalación seleccionada para actualizar la vista con la información relevante
  onInstalacionChange(): void {
    this.asignacionActual.instalacion = this.instalacionSeleccionada!;
    this.asignacionActual.puesto = 0;
    this.puestos = [];
    if (this.instalacionSeleccionada) {
      this.cargarPuestos(this.instalacionSeleccionada);
    }
  }

  // cargarInstalaciones se encarga de cargar las instalaciones correspondientes a un cliente específico, realizando una llamada al servicio para obtener esta información, y luego actualizando la vista con las instalaciones obtenidas, además de manejar los errores que puedan ocurrir durante el proceso para asegurar que la operación se realice correctamente. También permite preseleccionar una instalación y un puesto si se proporcionan los identificadores correspondientes
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

  //cargraPuestos se encarga de cargar los puestos correspondientes a una instalación específica, realizando una llamada al servicio para obtener esta información, y luego actualizando la vista con los puestos obtenidos, además de manejar los errores que puedan ocurrir durante el proceso para asegurar que la operación se realice correctamente. También permite preseleccionar un puesto si se proporciona el identificador correspondiente
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

  //abrirModalNuevo se encarga de abrir un diálogo para crear una nueva asignación, inicializando el estado del componente para reflejar que se está creando una nueva asignación, y luego mostrando el formulario correspondiente para que el usuario ingrese la información de la nueva asignación. Después de cerrar el diálogo, si se guardó la asignación, se actualiza el estado del componente con la nueva información y se llama al método para guardar la asignación en el backend
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
      autoFocus: false,
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

  //openSacafrancosModal se encarga de abrir un diálogo para mostrar los sacafrancos asociados a una semana, día, puesto y patrón específicos, permitiendo al usuario gestionar las asignaciones de sacafranco para esa combinación de parámetros, y luego actualizando la vista con los cambios realizados después de cerrar el diálogo, además de manejar los errores que puedan ocurrir durante el proceso para asegurar que la operación se realice correctamente
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
          this.loadCalendarWeeks();
        }
      });
    });
  }

  openSacafrancoFilaModal(fila: SacafrancoFila): void {
    if (!fila?.id) return;
    const ref = this.dialog.open(SacafrancoPersonasModalComponent, {
      width: '520px',
      maxHeight: '70vh',
      data: {
        assignedPersonaIds: this.getAssignedSacafrancoPersonaIds(),
        provincias: this.provinciasDisponibles,
        provinciaId: fila.provincia ?? null
      }
    });

    ref.afterClosed().subscribe(result => {
      if (!result?.personaId) return;
      this.asignacionService.actualizarSacafrancoFila(fila.id as number, {
        persona: result.personaId,
        provincia: result.provinciaId ?? null
      }).subscribe({
        next: updated => {
          const idx = (this.sacafrancoRows || []).findIndex(f => f?.id === updated.id);
          if (idx >= 0) this.sacafrancoRows[idx] = updated;
          this.buildDisplayRows();
          this.updateCalendarOrder();
        },
        error: err => console.error('Error al actualizar fila sacafranco', err)
      });
    });
  }

  //descargarReporteExcel se encarga de descargar un reporte de asignaciones en formato Excel para el mes y año seleccionados, realizando una llamada al backend para obtener el archivo como un blob, y luego utilizando la biblioteca FileSaver para guardar el archivo en el dispositivo del usuario con un nombre que incluye el mes y año, además de manejar los errores que puedan ocurrir durante el proceso para asegurar que la operación se realice correctamente
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

  //abrirModalEditar se encarga de abrir un diálogo para editar una asignación existente, inicializando el estado del componente con la información de la asignación seleccionada, y luego mostrando el formulario correspondiente para que el usuario pueda modificar la información de la asignación. Después de cerrar el diálogo, si se guardaron los cambios, se actualiza el estado del componente con la nueva información y se llama al método para guardar la asignación en el backend
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
      autoFocus: false,
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

  //guardarAsignacion se encarga de validar la información de la asignación actual antes de guardarla, asegurándose de que se hayan seleccionado un cliente, una instalación, un puesto, una persona y un horario. Si alguna de estas validaciones falla, se muestra una alerta al usuario indicando qué información falta. Si todas las validaciones pasan, se procede a guardar la asignación en el backend, ya sea creando una nueva asignación o actualizando una existente según el modo en que se encuentre el componente, y luego se actualiza la vista con los cambios realizados
  guardarAsignacion(): void {
    if (this.isSaving) return;

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

    const patronStart = this.asignacionActual.start_date || null;
    const resetCalendar = !!this.asignacionActual.patronAsignacion;

    if (this.modoEdicion && this.asignacionActual.id) {
      const payload = { 
        ...this.asignacionActual,
        patronAsignacion: this.asignacionActual.patronAsignacion || null,
        start_date: patronStart,
        recurring: true,
        end_date: null,
        reset_calendar: resetCalendar
      } as any;
      this.isSaving = true;
      this.asignacionService.actualizarAsignacion(
        this.asignacionActual.id,
        payload
      ).subscribe({
        next: () => {
          Swal.fire({ icon: 'success', title: 'Asignación actualizada', timer: 1200, showConfirmButton: false });
          this.cargarAsignaciones();
          this.resetAsignacionState();
          this.loadCalendarWeeks();
          this.isSaving = false;
        },
        error: err => {
          console.error(err);
          const detail = err?.error ? JSON.stringify(err.error) : 'No se pudo actualizar la asignación';
          Swal.fire({ icon: 'error', title: 'Error', text: detail });
          this.isSaving = false;
        }
      });
    } else {
      // Forzar creación de calendario semanal al crear la asignación
      const payload = { 
        ...this.asignacionActual,
        patronAsignacion: this.asignacionActual.patronAsignacion || null,
        start_date: patronStart,
        create_calendar: true,
        recurring: true,
        end_date: null
      } as any;
      this.isSaving = true;
      this.asignacionService.crearAsignacion(payload).subscribe({
        next: () => {
          Swal.fire({ icon: 'success', title: 'Asignación creada', timer: 1200, showConfirmButton: false });
          this.cargarAsignaciones();
          this.resetAsignacionState();
          this.loadCalendarWeeks();
          this.isSaving = false;
        },
        error: err => {
          console.error(err);
          const detail = err?.error ? JSON.stringify(err.error) : 'No se pudo crear la asignación';
          Swal.fire({ icon: 'error', title: 'Error', text: detail });
          this.isSaving = false;
        }
      });
    }
  }

  //buildRowForPuesto se encarga de construir una fila de visualización para un puesto específico, utilizando la información del puesto y sus horarios para determinar qué días de la semana están asociados con ese puesto, y luego creando un objeto que representa la fila con los detalles del puesto y las celdas correspondientes a cada día de la semana, lo que permite mostrar esta información de manera organizada en la vista
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

  //eliminarAsignacion se encarga de eliminar una asignación específica, mostrando una confirmación al usuario antes de realizar la eliminación, y luego actualizando la vista para reflejar la eliminación de la asignación, además de manejar los errores que puedan ocurrir durante el proceso para asegurar que la operación se realice correctamente
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
          this.loadCalendarWeeks();
        },
        error: err => {
          console.error(err);
          Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo eliminar la asignación' });
        }
      });
    });
  }

  //cambiarMesAnio se encarga de manejar el cambio en la selección del mes o año para las asignaciones, llamando al método para cargar las asignaciones correspondientes al nuevo mes y año seleccionados, lo que permite actualizar la vista con la información relevante para el período seleccionado por el usuario
  cambiarMesAnio(): void {
    this.cargarAsignaciones();
  }

  //resetAsignacionState se encarga de restablecer el estado relacionado con la asignación actual, limpiando la información de la asignación, las selecciones de cliente e instalación, y los listados de instalaciones y puestos, lo que prepara el componente para crear una nueva asignación o para limpiar el formulario después de guardar o cancelar una operación
  private resetAsignacionState(): void {
    this.asignacionActual = this.nuevaAsignacion();
    this.clienteSeleccionado = null;
    this.instalacionSeleccionada = null;
    this.instalaciones = [];
    this.puestos = [];
  }
}
