import { CommonModule } from '@angular/common';
import { Component, OnInit, ViewChildren, QueryList, AfterViewInit } from '@angular/core';
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
import { AsignacionCalendarioComponent } from '../asignacion-calendario/asignacion-calendario.component';
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
import { SacafrancoPersonasModalComponent } from './sacafranco-personas-modal/sacafranco-personas-modal.component';
import { ReporteAsistenciaColorDialogComponent } from '../reporte-asistencia/dialogs/reporte-asistencia-color-dialog.component';

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
  displayRows: Array<
    { type: 'asignacion'; asig: Asignacion; isGroupedChild: boolean } |
    { type: 'sacafranco'; id: number; fila: SacafrancoFila }
  > = [];
  displayAssignmentRows: Asignacion[] = [];
  sacafrancoRows: SacafrancoFila[] = [];
  draggingAsignacionId: number | null = null;
  private lastDragPoint: { x: number; y: number } | null = null;
  private pendingPatronId: number | null = null;

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

  // Obtiene la fecha de inicio del mes actual como un string en formato YYYY-MM-DD para inicializar el calendario
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
  
  // Maneja el cambio de fecha compartida, actualizando el estado del componente y recargando las asignaciones para reflejar la nueva fecha seleccionada
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

  // onMonthChange se encarga de manejar el cambio de mes en el calendario, actualizando el estado del componente y recargando las asignaciones para reflejar el nuevo mes seleccionado
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

  //onFiltroChange se encarga de manejar el cambio en el filtro de texto, recargando las asignaciones para reflejar el nuevo filtro aplicado y actualizando los calendarios para mostrar la información filtrada correctamente
  onFiltroChange(): void {
    this.cargarAsignaciones();
    if (this.calendarios && this.calendarios.length) {
      this.calendarios.forEach(c => c.loadWeek());
    }
  }

  // hideMultipleSelectionIndicator se utiliza para ocultar el indicador de selección múltiple en la vista, devolviendo siempre true para indicar que no se deben mostrar indicadores adicionales incluso si hay múltiples elementos seleccionados
  hideMultipleSelectionIndicator(): boolean {
    return true;
  }

  // columnaOculta se encarga de verificar si una columna específica está oculta en la vista, comprobando si la clave de la columna se encuentra en el arreglo de columnas ocultas y devolviendo un booleano para indicar su estado
  columnaOculta(key: string): boolean {
    return this.columnasOcultas.includes(key);
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
    if (!this.columnaOculta('cliente')) count += 1;
    if (this.mostrarPuesto()) count += 2;
    if (!this.columnaOculta('cedula')) count += 1;
    if (!this.columnaOculta('persona')) count += 1;
    if (!this.columnaOculta('accion')) count += 1;
    return count || 1;
  }

  //canDeleteSacafrancoFila se encarga de determinar si una fila de sacafranco puede ser eliminada, verificando si la fila pertenece al mes y año actuales o posteriores, devolviendo un booleano para indicar si se permite la eliminación
  canDeleteSacafrancoFila(fila?: SacafrancoFila | null): boolean {
    if (!fila) return false;
    if (fila.anio < this.anio) return false;
    if (fila.anio === this.anio && fila.mes < this.mes) return false;
    return true;
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
    this.asignacionService.obtenerAsignaciones(this.mes, this.anio, params).subscribe({
      next: data => {
        this.asignaciones = data || [];
        this.buildDisplayRows();
        this.updateCalendarOrder();
      },
      error: err => console.error('Error al cargar asignaciones', err)
    });

    this.asignacionService.obtenerSacafrancoFilas(this.mes, this.anio).subscribe({
      next: data => {
        this.sacafrancoRows = data || [];
        this.buildDisplayRows();
        this.updateCalendarOrder();
      },
      error: err => console.error('Error al cargar filas sacafranco', err)
    });
  }

  //crearSacafrancoFila se encarga de abrir un diálogo para seleccionar una persona y luego crear una nueva fila de sacafranco asociada a esa persona para el mes y año seleccionados, realizando una llamada al servicio correspondiente para guardar la nueva fila, y luego actualizando la vista con la nueva información, además de manejar los errores que puedan ocurrir durante el proceso para asegurar que la operación se realice correctamente
  crearSacafrancoFila(): void {
    const ref = this.dialog.open(SacafrancoPersonasModalComponent, {
      width: '520px'
    });

    ref.afterClosed().subscribe(result => {
      if (!result?.personaId) return;

      const payload: SacafrancoFila = {
        mes: this.mes,
        anio: this.anio,
        orden: (this.sacafrancoRows || []).length,
        persona: result.personaId
      };

      this.asignacionService.crearSacafrancoFila(payload).subscribe({
        next: fila => {
          this.sacafrancoRows = [...(this.sacafrancoRows || []), fila].filter(f => f && f.id);
          this.buildDisplayRows();
          this.updateCalendarOrder();
        },
        error: err => console.error('Error al crear fila sacafranco', err)
      });
    });
  }

  //editarSacafrancoFila se encarga de abrir un diálogo para seleccionar una persona y luego actualizar la fila de sacafranco asociada a esa persona para el mes y año seleccionados, realizando una llamada al servicio correspondiente para guardar los cambios, y luego actualizando la vista con la nueva información, además de manejar los errores que puedan ocurrir durante el proceso para asegurar que la operación se realice correctamente
  editarSacafrancoFila(fila: SacafrancoFila): void{
    const ref = this.dialog.open(SacafrancoPersonasModalComponent, {
      width: '520px',
      data: { personas: this.personas }
    });
    ref.afterClosed().subscribe(result => {
      if (!result?.personaId) return;

      const payload: Partial<SacafrancoFila> = {
        persona: result.personaId
      };
    })
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

    moveItemInArray(this.displayRows, event.previousIndex, event.currentIndex);

    const orderableRows = (this.displayRows || []).filter(r =>
      r?.type === 'sacafranco' || r?.type === 'asignacion'
    );

    const ordenAsignaciones: { id: number; orden: number }[] = [];
    const ordenSacafranco: { id: number; orden: number }[] = [];

    orderableRows.forEach((row, idx) => {
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
    this.lastDragPoint = null;
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
    const asignaciones = this.asignaciones || [];
    const sacRows = this.sacafrancoRows || [];

    const rows: Array<
      { type: 'asignacion'; asig: Asignacion; isGroupedChild: boolean } |
      { type: 'sacafranco'; id: number; fila: SacafrancoFila }
    > = [];
    const displayAssignments: Asignacion[] = [];

    const orderables: Array<{ kind: 'asignacion'; asig: Asignacion } | { kind: 'sacafranco'; fila: SacafrancoFila }> = [
      ...asignaciones.map(a => ({ kind: 'asignacion' as const, asig: a })),
      ...sacRows.map(f => ({ kind: 'sacafranco' as const, fila: f }))
    ];

    orderables
      .sort((a, b) => {
        const aOrd = a.kind === 'asignacion' ? (a.asig.orden ?? 0) : (a.fila.orden ?? 0);
        const bOrd = b.kind === 'asignacion' ? (b.asig.orden ?? 0) : (b.fila.orden ?? 0);
        return aOrd - bOrd;
      })
      .forEach(item => {
        if (item.kind === 'asignacion') {
          rows.push({ type: 'asignacion', asig: item.asig, isGroupedChild: false });
          displayAssignments.push(item.asig);
          return;
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
    setTimeout(() => {
      this.lastDragPoint = null;
    }, 0);
  }

  //onDragMoved se encarga de manejar el evento de movimiento durante el arrastre de una asignación, actualizando las coordenadas del último punto de arrastre para mantener un seguimiento de la posición del cursor mientras se realiza el arrastre, lo que puede ser útil para mostrar indicadores visuales o realizar cálculos relacionados con la posición durante el proceso de arrastre
  onDragMoved(event: CdkDragMove): void {
    const point = event?.pointerPosition;
    if (!point) return;
    this.lastDragPoint = { x: point.x, y: point.y };
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
    return row?.asig?.id ?? index;
  }

  //prevWeekAndPage se encarga de navegar a la semana anterior en el calendario y actualizar la vista para reflejar los cambios, iterando sobre los componentes de calendario disponibles y llamando a su método para cargar la semana anterior, lo que permite al usuario ver las asignaciones correspondientes a esa semana
  prevWeekAndPage(): void {
    if (this.calendarios) this.calendarios.forEach(c => { try { c.prevWeek(); } catch(e){} });
  }

  //nextWeekAndPage se encarga de navegar a la semana siguiente en el calendario y actualizar la vista para reflejar los cambios, iterando sobre los componentes de calendario disponibles y llamando a su método para cargar la semana siguiente, lo que permite al usuario ver las asignaciones correspondientes a esa semana
  nextWeekAndPage(): void {
    if (this.calendarios) this.calendarios.forEach(c => { try { c.nextWeek(); } catch(e){} });
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
      start_date: null,
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
          if (this.calendarios) this.calendarios.forEach(c => c.loadWeek());
        }
      })
    
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
          const detail = err?.error ? JSON.stringify(err.error) : 'No se pudo actualizar la asignación';
          Swal.fire({ icon: 'error', title: 'Error', text: detail });
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
      this.asignacionService.crearAsignacion(payload).subscribe({
        next: () => {
          Swal.fire({ icon: 'success', title: 'Asignación creada', timer: 1200, showConfirmButton: false });
          this.cargarAsignaciones();
          this.resetAsignacionState();
          if (this.calendarios) this.calendarios.forEach(c => c.loadWeek());
        },
        error: err => {
          console.error(err);
          const detail = err?.error ? JSON.stringify(err.error) : 'No se pudo crear la asignación';
          Swal.fire({ icon: 'error', title: 'Error', text: detail });
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
          if (this.calendarios) this.calendarios.forEach(c => c.loadWeek());
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
