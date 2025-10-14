import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HostPage } from './host-page';

describe('HostPage', () => {
  let component: HostPage;
  let fixture: ComponentFixture<HostPage>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostPage]
    })
    .compileComponents();

    fixture = TestBed.createComponent(HostPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
