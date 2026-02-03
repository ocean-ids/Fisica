import { CommonModule } from '@angular/common';
import { Component, OnInit, ViewChild, AfterViewInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Cliente, Persona, Instalacion, Puesto, Horario, Asignacion } from '../../models';
import { ClienteService } from '../../services/cliente.service';
import { InstalacionService } from '../../services/instalacion.service';
import { PuestoService } from '../../services/puesto.service';
import { PersonaService } from '../../services/persona.service';
import { HorarioService } from '../../services/horario.service';
import { AsignacionService } from '../../services/asignacion.service';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatCardModule } from '@angular/material/card';
import { MatMenuModule } from '@angular/material/menu';
import { AsignacionCalendarioComponent } from '../asignacion-calendario/asignacion-calendario.component';
import { HttpClient } from '@angular/common/http';
import { saveAs } from 'file-saver';

@Component({
  selector: 'app-asignaciones',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatCardModule
    ,MatMenuModule
    ,AsignacionCalendarioComponent
  ],
  templateUrl: './asignaciones.component.html',
  styleUrl: './asignaciones.component.css'
})
export class AsignacionesComponent implements OnInit {

  @ViewChild(AsignacionCalendarioComponent)
  calendario?: AsignacionCalendarioComponent;

  ngAfterViewInit(): void {
    // Suscribirse a cambios de semana del calendario para sincronizar filtros
    setTimeout(() => {
      if (this.calendario && this.calendario.weekStartChange) {
        this.calendario.weekStartChange.subscribe((ws: string) => {
          if (!ws) return;
          // ws es YYYY-MM-DD (lunes). Usarlo como día filtro en asignaciones
          this.dia = ws;
          const parts = ws.split('-');
          if (parts.length === 3) {
            this.anio = Number(parts[0]);
            this.mes = Number(parts[1]);
            this.monthValue = `${this.anio}-${String(this.mes).padStart(2,'0')}`;
          }
          this.cargarAsignaciones();
        });
      }
    }, 0);
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
    if (this.calendario) {
      this.calendario.weekStart = this.dia;
      this.calendario.loadWeek();
    }
    this.cargarAsignaciones();
  }

  textoBotonAsignacion: string = 'Guardar';

  asignaciones: Asignacion[] = [];

  mes: number = new Date().getMonth() + 1;
  anio: number = new Date().getFullYear();
  dia: string | null = null; // formato YYYY-MM-DD (opcional)
  monthValue: string = '';

  clientes: Cliente[] = [];
  personas: Persona[] = [];
  horarios: Horario[] = [];
  instalaciones: Instalacion[] = [];
  puestos: Puesto[] = [];

  clienteSeleccionado: number | null = null;
  instalacionSeleccionada: number | null = null;

  mostrarModal: boolean = false;
  asignacionActual: Asignacion = this.nuevaAsignacion();
  modoEdicion: boolean = false;

  constructor(
    private clienteService: ClienteService,
    private instalacionService: InstalacionService,
    private puestoService: PuestoService,
    private personaService: PersonaService,
    private horarioService: HorarioService,
    private asignacionService: AsignacionService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.cargarCatalogos();
    // inicializar selector mensual y cargar asignaciones
    this.monthValue = `${this.anio}-${String(this.mes).padStart(2,'0')}`;
    this.cargarAsignaciones();
  }

  onMonthChange(): void {
    if (!this.monthValue) return;
    const parts = this.monthValue.split('-');
    if (parts.length !== 2) return;
    this.anio = Number(parts[0]);
    this.mes = Number(parts[1]);
    this.dia = null;
    this.cargarAsignaciones();

    // calcular el primer lunes del mes y sincronizar calendario
    const firstMonday = this.getFirstMonday(this.anio, this.mes);
    if (this.calendario) {
      this.calendario.weekStart = firstMonday;
      this.calendario.loadWeek();
    }
  }

  private getFirstMonday(year: number, month: number): string {
    const d = new Date(year, month - 1, 1);
    const day = d.getDay(); // 0..6 Sun..Sat
    const offset = (8 - day) % 7; // days to add to reach Monday
    const dayOfMonth = 1 + offset;
    const mm = String(month).padStart(2, '0');
    const dd = String(dayOfMonth).padStart(2, '0');
    return `${year}-${mm}-${dd}`;
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
  }

  cargarAsignaciones(): void {
    this.asignacionService.obtenerAsignaciones(this.mes, this.anio).subscribe({
      next: data => {
        // Mostrar todas las asignaciones del mes/año (no filtrar por día)
        this.asignaciones = data;
      },
      error: err => console.error('Error al cargar asignaciones', err)
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
      clienteCodigo: ''
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
      this.instalacionService.getInstalaciones().subscribe({
        next: data => {
          this.instalaciones = data.filter(
            i => i.cliente_id === this.clienteSeleccionado
          );
        },
        error: err => console.error('Error al cargar instalaciones', err)
      });
    }
  }

  onInstalacionChange(): void {
    this.asignacionActual.instalacion = this.instalacionSeleccionada!;
    this.asignacionActual.puesto = 0;
    this.puestos = [];

    if (this.instalacionSeleccionada) {
      this.puestoService.getPuestosPorInstalacion(this.instalacionSeleccionada)
        .subscribe({
          next: data => this.puestos = data,
          error: err => console.error('Error al cargar puestos', err)
        });
    }
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
   
    if (this.instalacionSeleccionada) {
      this.onInstalacionChange();
    }
    this.mostrarModal = true;
  }

  descargarReporteExcel() {
  this.http.get('http://localhost:8000/api/reporte-asignaciones/', { responseType: 'blob' })
    .subscribe(blob => {
      saveAs(blob, 'reporte_asignaciones.xlsx');
    });
  }

  abrirModalEditar(asignacion: Asignacion): void {
    this.modoEdicion = true;
    this.textoBotonAsignacion = 'Actualizar';
    this.asignacionActual = { ...asignacion };

    this.clienteSeleccionado = asignacion.cliente;
    this.instalacionSeleccionada = asignacion.instalacion;

    this.onClientChange();
    this.onInstalacionChange();

    this.mostrarModal = true;
  }

  cerrarModal(): void {
    this.mostrarModal = false;
    this.asignacionActual = this.nuevaAsignacion();
    this.clienteSeleccionado = null;
    this.instalacionSeleccionada = null;
    this.instalaciones = [];
    this.puestos = [];
  }

  guardarAsignacion(): void {

    if (!this.clienteSeleccionado) {
      alert('Debe seleccionar un Cliente');
      return;
    }
    if (!this.instalacionSeleccionada) {
      alert('Debe seleccionar una Instalación');
      return;
    }
    if (!this.asignacionActual.puesto) {
      alert('Debe seleccionar un Puesto');
      return;
    }
    if (!this.asignacionActual.persona) {
      alert('Debe seleccionar una Persona');
      return;
    }
    if (!this.asignacionActual.horario) {
      alert('Debe seleccionar un Horario');
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
      alert('Ya existe una asignación para esta persona en este mes.');
      return;
    }

    // No enviar fecha exacta: las asignaciones se guardan por mes y año
    // (this.asignacionActual as any).fecha = this.dia ? this.dia : null;

    if (this.modoEdicion && this.asignacionActual.id) {
      this.asignacionService.actualizarAsignacion(
        this.asignacionActual.id,
        this.asignacionActual
      ).subscribe({
        next: () => {
          alert('Asignación actualizada');
          this.cargarAsignaciones();
          this.cerrarModal();
          this.calendario?.loadWeek();
        },
        error: err => {
          console.error(err);
          alert('Error al actualizar');
        }
      });
    } else {
      this.asignacionService.crearAsignacion(this.asignacionActual).subscribe({
        next: () => {
          alert('Asignación creada');
          this.cargarAsignaciones();
          this.cerrarModal();
          // No crear filas semanales automáticamente aquí; el backend puede propagar semanas desde la asignación mensual
          this.calendario?.loadWeek();
        },
        error: err => {
          console.error(err);
          alert('Error al crear');
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

    const dias = (puesto && puesto.dias) ? (Array.isArray(puesto.dias) ? puesto.dias : [puesto.dias]) : [];
    const diasNorm = dias.map(normalize).filter((x:any)=>x);
    const turno = (puesto && puesto.turno) ? String(puesto.turno).trim().toLowerCase() : '';
    const defaultCode = turno.startsWith('n') ? 'N' : 'D';

    const row: any = { puesto: puestoId, puesto_detalle: puesto };
    const names = ['lunes','martes','miercoles','jueves','viernes','sabado','domingo'];
    for (let i=0;i<7;i++){
      const match = diasNorm.some((d:any)=> d===names[i] || names[i].includes(d) || d.includes(names[i]));
      row[weekdayKeys[i]] = match ? defaultCode : '';
    }
    return row;
  }

  eliminarAsignacion(asignacion: Asignacion): void {
    if (confirm(`¿Eliminar la asignación de ${asignacion.persona_detalle?.apellidos} ${asignacion.persona_detalle?.nombres} (${asignacion.persona_detalle?.tipo})?`)) {
      this.asignacionService.eliminarAsignacion(asignacion.id!).subscribe({
        next: () => {
          alert('Asignación eliminada');
          this.cargarAsignaciones();
          this.calendario?.loadWeek();
        },
        error: err => {
          console.error(err);
          alert('Error al eliminar');
        }
      });
    }
  }

  cambiarMesAnio(): void {
    this.cargarAsignaciones();
  }
}
