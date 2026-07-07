function DoFISH(Tracked, FISH)

% global variable
AllImg = [];

channel_num = [];
sigma = 1; % dot size (unit pixel)

type1 = 'both'; %exist in both channels
type3 = 'channel 1 only'; %exist only in channel
type6 = 'channel 2 only';


ParseArguments(nargin)

    function ParseArguments(pnumin)
        if pnumin==0 % Zero input, i.e. no "FISH", no "Tracked" 
            % create empty "Tracked" for next steps
            
            Tracked{1}.dirname = '';
            Tracked{1}.filename = {};
            
            FISH = [];
            
            %open the images
            olddir=pwd;
            if ~isdir(Tracked{1}.dirname)
                directory=uigetdir(olddir,'Select a new directory with image files');
                for i=1:length(Tracked)
                    Tracked{i}.dirname=[directory filesep];
                end
            end
            cd(Tracked{1}.dirname);
            
            % choose which channel to load
            f=[dir('*TIF'),dir('*tif')];
            [~,~,~,chlist, ~, ~, namehead]=regexp([f.name],'_w[^_]*');
            [~,~,~, framelist]=regexp([f.name],'_s[\d]*'); %
            chlist=unique(chlist);
            framelist=unique(framelist);
            chlistname=cellfun(@(x) x(3:end), unique(chlist),'unif',0);
            framename=cellfun(@(x) x(3:end), unique(framelist),'unif',0);
            chsel=listdlg('ListString', chlistname, 'ListSize',[160,80]); %'SelectionMode','single', 
            channel=chlist(chsel); 
            channel_num = length(channel);
            
            AllImg=cell(channel_num,length(framename));
            hh = waitbar(0,'Loading Images...');
            for cframe=1:length(framename)
                waitbar(cframe/length(framename),hh)
                for n = 1:channel_num
                    Tracked{cframe}.filename = strcat(namehead(1),chlist{chsel(n)},framelist{cframe}, '.tif');
                    Tfilename = Tracked{cframe}.filename;
                    [~,~,~,frame_name]=regexp(Tfilename,'_s[^_]*.tif');
                    im_bs = loadImage(strcat(namehead(1),chlist{chsel(n)},frame_name{:}));
                    if isempty(im_bs)
                        disp(strcat('Cannot find ', Tfilename));
                        return
                    end
                    AllImg{n,cframe}=im_bs;
                    FISH{n,1}.channel = channel(n);
                    Tracked{cframe}.cells = {};
                    FISH{n,cframe}.cells = {};
                end
            end
            for n = 1:channel_num
                [FISH{n,1}.H_thres_default, FISH{n,1}.f, FISH{n,1}.X, FISH{n,1}.Y] = estimate_H_thres(n);
                FISH{n,1}.H_thres = FISH{n,1}.H_thres_default;
            end
            delete(hh)
            DisplayTrack;          
            
        elseif iscell(Tracked) && pnumin==1  %the arguments are the tracked structure, but without FISH data
            FISH = [];
            
            %open the images
            olddir=pwd;
            if ~isdir(Tracked{1}.dirname)
                directory=uigetdir(olddir,'Select a new directory with image files');
                for i=1:length(Tracked)
                    Tracked{i}.dirname=[directory filesep];
                end
            end
            cd(Tracked{1}.dirname);
            
            % choose which channel to load
            f=[dir('*TIF'),dir('*tif')];
            [~,~,~,chlist, ~, ~, namehead]=regexp([f.name],'_w[^_]*');
            chlist=unique(chlist);
            chlistname=cellfun(@(x) x(3:end), unique(chlist),'unif',0);
            chsel=listdlg('ListString', chlistname, 'ListSize',[160,80]); %'SelectionMode','single', 
            channel=chlist(chsel); 
            channel_num = length(channel);
            
            AllImg=cell(channel_num,length(Tracked));
            hh = waitbar(0,'Loading Images...');
            for cframe=1:length(Tracked)
                waitbar(cframe/length(Tracked),hh)
                for n = 1:channel_num
                    Tfilename = Tracked{cframe}.filename;
                    [~,~,~,frame_name]=regexp(Tfilename,'_s[^_]*.tif');
                    im_bs = loadImage(strcat(namehead(1),chlist{chsel(n)},frame_name{:}));
                    AllImg{n,cframe}=im_bs;
                    FISH{n,1}.channel = channel(n);
                    for num_cell = 1:length(Tracked{cframe}.cells)
                        FISH{n,cframe}.cells{num_cell}=[];
                    end
                end
            end
            for n = 1:channel_num
                [FISH{n,1}.H_thres_default, FISH{n,1}.f, FISH{n,1}.X, FISH{n,1}.Y] = estimate_H_thres(n);
                FISH{n,1}.H_thres = FISH{n,1}.H_thres_default;
            end
            delete(hh)
            DisplayTrack;            
        elseif iscell(Tracked) && iscell(FISH)  % load both Tracked and FISH
            %open the images
            olddir=pwd;
            cd(Tracked{1}.dirname);
            
            % load all channels
            [nch, ~] = size(FISH); % 
            for n = 1:nch
                chlist(n) = FISH{n,1}.channel;
            end
            chsel = 1:length(chlist);
            channel = chlist(chsel); 
            channel_num = length(channel);
            
            AllImg=cell(channel_num,length(Tracked));
            hh = waitbar(0,'Loading Images...');
            for cframe=1:length(Tracked)
                waitbar(cframe/length(Tracked),hh)
                for n = 1:channel_num
                    Tfilename = Tracked{cframe}.filename;
                    [~,~,~,frame_name]=regexp(Tfilename,'_s[^_]*.tif');
                    [~,~,~,~, ~, ~, namehead]=regexp(Tfilename,'_w[^_]*');
                    im_bs = loadImage(strcat(namehead{1}{1},chlist{chsel(n)},frame_name{:}));
                    AllImg{n,cframe}=im_bs;
                end
            end
            
            for n = 1:channel_num
                [FISH{n,1}.H_thres_default, FISH{n,1}.f, FISH{n,1}.X, FISH{n,1}.Y] = estimate_H_thres(n);
                FISH{n,1}.H_thres = FISH{n,1}.H_thres_default;
            end
            
            delete(hh)
            DisplayTrack;
        end
    end

    function newtarget=AddCell(target, targetpos, cellvalue, cellpos)
        relativepos=cellpos-targetpos;
        %find the coordinates of the region inside the target and inside the cellvalue
        trgtXslice=max(1,relativepos(1)+1):min(size(target,1),relativepos(1)+size(cellvalue,1));
        trgtYslice=max(1,relativepos(2)+1):min(size(target,2),relativepos(2)+size(cellvalue,2));
        cellXslice=max(1,-relativepos(1)+1):min(size(cellvalue,1), size(target,1)-relativepos(1));
        cellYslice=max(1,-relativepos(2)+1):min(size(cellvalue,2), size(target,2)-relativepos(2));
        %put the cell values inside target
        newtarget=target;
        newtarget(trgtXslice,trgtYslice)=target(trgtXslice,trgtYslice)+cellvalue(cellXslice,cellYslice);
    end
    function image=SegRenderNum(cells,imy,imx)
        if isempty(cells)
            if ~exist('imy','var') || ~exist('imx','var')
                image=[];
            else
                image=zeros(imy,imx);
            end
            return
        end
        cellpos=cell2mat({cells.pos}');
        cellsize=cell2mat({cells.size}');
        if ~exist('imy','var')
            ystart=min(cellpos(:,1));
            ystop=max(cellpos(:,1)+cellsize(:,1)-1);
        else
            ystart=1;
            ystop=imy;
        end
        if ~exist('imx','var')
            xstart=min(cellpos(:,2));
            xstop=max(cellpos(:,2)+cellsize(:,2)-1);
        else
            xstart=1;
            xstop=imx;
        end
        
        image=zeros(ystop-ystart+1,xstop-xstart+1);
        for j=1:length(cells)
            image=AddCell(image,[ystart,xstart],(j)*cells(j).mask,cells(j).pos);
        end
    end
    function image=SegRenderCnt(cells,imy,imx)
        if isempty(cells)
            image=[];
            return
        end
        cellpos=cell2mat({cells.pos}');
        cellsize=cell2mat({cells.size}');
        if ~exist('imy','var')
            ystart=min(cellpos(:,1));
            ystop=max(cellpos(:,1)+cellsize(:,1)-1);
        else
            ystart=1;
            ystop=imy;
        end
        if ~exist('imx','var')
            xstart=min(cellpos(:,2));
            xstop=max(cellpos(:,2)+cellsize(:,2)-1);
        else
            xstart=1;
            xstop=imx;
        end
        
        image=zeros(ystop-ystart+1,xstop-xstart+1);
        for j=1:length(cells)
            image=AddCell(image,[ystart,xstart],cells(j).mask,cells(j).pos);
        end
    end

    % New helpers for nucleus-cytoplasm pairing (7/7/2026)
    function yesno = is_dapi_channel(channel_value)
        % Return true when one selected channel is the DAPI channel
        yesno = contains(upper(char(channel_value)), 'DAPI');
    end

    function mask_value = get_cell_mask(cell_data, channel_index)
        % Return the mask DoFISH should use for the selected channel
        channel_value = FISH{channel_index,1}.channel;
        if is_dapi_channel(channel_value) && isfield(cell_data, 'nucleus_mask')
            if ~isempty(cell_data.nucleus_mask)
                mask_value = cell_data.nucleus_mask;
                return
            end
        end
        mask_value = cell_data.mask;
    end

    % find FISH dot mask
    function [mask_H, bg] = dot_mask(data)
        cx = floor(8*sigma); %size of the gaussian kernel
        sizex = 2*cx-1;
        [x,y] = meshgrid(1:sizex,1:sizex);
        G = exp(-0.5*(x-cx).^2./(sigma^2)-0.5*(y-cx).^2./(sigma^2));
        G = G./(2*pi*sigma^2); %normalization
        
        square_2d = zeros(sizex)+1;
        square_2d = square_2d/sum(square_2d(:));
        
        annulus_2d = zeros(sizex)+1;
        annulus_2d(floor(cx*0.25):ceil(cx*1.75),floor(cx*0.25):ceil(cx*1.75)) = 0;
        annulus_2d(annulus_2d>0) = 1;
        
        
        [H,bg] = wavelet_cell(data, G, square_2d, annulus_2d);
        mask_H = H; 
    end
    function [H, bg] = wavelet_cell(data, G, square_2d, annulus_2d)
        
        [sizex, sizey] = size(data);
        H(1:sizex, 1:sizey) = 0;
        bg(1:sizex, 1:sizey) = 0;
        M(1:sizex, 1:sizey) = 0;
        
        edge = (length(square_2d)-1)/2;
        
        
        % to avoid the ZEROS pixel edges, do the convolution manually
        for i0 = edge+1 : sizex-edge
            for j0 = edge+1 : sizey-edge
                data_seg = data((i0-edge):(i0+edge),(j0-edge):(j0+edge));
                if isempty(find(data_seg == 0, 1)) %there is NOT 0 intensity pixel in the area
                    M(i0,j0) = data(i0,j0) - sum(sum(square_2d.*data_seg));
                    background = annulus_2d.*data_seg;
                    bg(i0,j0) = median(nonzeros(background));
                end
            end
        end
        for i0 = edge+1 : sizex-edge
            for j0 = edge+1 : sizey-edge
                data_seg = data((i0-edge):(i0+edge),(j0-edge):(j0+edge));
                if isempty(find(data_seg == 0, 1)) %there is NOT 0 intensity pixel in the origial area
                    M_seg = M((i0-edge):(i0+edge),(j0-edge):(j0+edge));
                    H(i0,j0) = sum(sum(G.*M_seg))*sqrt(2*pi*sigma^2);
                end
            end
        end
    end

    % find H threshold
    function [H_thres, f, X, Y] = estimate_H_thres(channel)
        all_maxH  = [];
        for cframe=1:min(length(Tracked),10)
            for num_cell = 1:length(Tracked{1,cframe}.cells)
                if length(all_maxH)<1000
                    if isfield(Tracked{1,cframe}.cells{num_cell}, 'pos')
                        pos_x = Tracked{1,cframe}.cells{num_cell}.pos(1);
                        pos_y = Tracked{1,cframe}.cells{num_cell}.pos(2);
                        size_x = Tracked{1,cframe}.cells{num_cell}.size(1);
                        size_y = Tracked{1,cframe}.cells{num_cell}.size(2);
                        im_temp = AllImg{channel,cframe};
                        cell_mask = get_cell_mask(Tracked{1,cframe}.cells{num_cell}, channel);
                        cell_image = cell_mask.*im_temp(pos_x:pos_x+size_x-1, pos_y:pos_y+size_y-1);
                        [FISH{channel, cframe}.cells{num_cell}.mask_H, FISH{channel, cframe}.cells{num_cell}.bg] = dot_mask(cell_image);
                    end
                    mask = FISH{channel, cframe}.cells{num_cell}.mask_H;
                    maxH = mask.*imregionalmax(mask).*(mask>0);
                    all_maxH = [nonzeros(all_maxH)', nonzeros(maxH)'];
                end
            end
        end
        
        if length(all_maxH)<10
            H_thres = 10;
            f = [];
            X = [];
            Y = [];
        else
            [N, edges] = histcounts(all_maxH, 'BinWidth', 1);
            Y = N;
            X = edges(1:end-1) + (edges(2)-edges(1))/2;
            options = fitoptions('gauss1');
            options.Lower = [0 1 0];
            options.Upper = [Inf 100 Inf];
            f=fit(X',Y','gauss1',options);
            H_thres = f.b1 + 2*f.c1; %prctile(all_maxH, 90);
        end
    end

    % select dots
    function pickdots(frame, num, selectcell)
        if ~exist('selectcell')
            for num_cell = 1:length(Tracked{frame}.cells)
                FISH{num, frame}.cells{num_cell}.dots = {};
                if isfield(Tracked{frame}.cells{num_cell}, 'pos')
                    FISH{num, frame}.cells{num_cell}.dots = {};
                    pos_x = Tracked{frame}.cells{num_cell}.pos(1);
                    pos_y = Tracked{frame}.cells{num_cell}.pos(2);
                    size_x = Tracked{frame}.cells{num_cell}.size(1);
                    size_y = Tracked{frame}.cells{num_cell}.size(2);
                    im_temp = AllImg{num,frame};
                    cell_mask = get_cell_mask(Tracked{frame}.cells{num_cell}, num);
                    cell_image = cell_mask.*im_temp(pos_x:pos_x+size_x-1, pos_y:pos_y+size_y-1);
                    [FISH{num, frame}.cells{num_cell}.mask_H, FISH{num, frame}.cells{num_cell}.bg] = dot_mask(cell_image);
                    FISH{num, frame}.cells{num_cell}.dots = identify_dots(cell_image, FISH{num, frame}.cells{num_cell}.mask_H,...
                        FISH{num, frame}.cells{num_cell}.bg, FISH{num,1}.H_thres);
                end
            end
        else
            FISH{num, frame}.cells{selectcell}.dots = {};
            if isfield(Tracked{frame}.cells{selectcell}, 'pos')
                FISH{num, frame}.cells{selectcell}.dots = {};
                pos_x = Tracked{frame}.cells{selectcell}.pos(1);
                pos_y = Tracked{frame}.cells{selectcell}.pos(2);
                size_x = Tracked{frame}.cells{selectcell}.size(1);
                size_y = Tracked{frame}.cells{selectcell}.size(2);
                im_temp = AllImg{num,frame};
                cell_mask = get_cell_mask(Tracked{frame}.cells{selectcell}, num);
                cell_image = cell_mask.*im_temp(pos_x:pos_x+size_x-1, pos_y:pos_y+size_y-1);
                [FISH{num, frame}.cells{selectcell}.mask_H, FISH{num, frame}.cells{selectcell}.bg] = dot_mask(cell_image);
                FISH{num, frame}.cells{selectcell}.dots = identify_dots(cell_image, FISH{num, frame}.cells{selectcell}.mask_H,...
                    FISH{num, frame}.cells{selectcell}.bg, FISH{num,1}.H_thres);
            end
        end
    end
    function dots = identify_dots(data, mask_H, bg, lim_H)
        if isempty(mask_H)
            dots = {};
            return;
        end
        
        dots = {};
        mask = imregionalmax(mask_H).*(mask_H>lim_H);
        [row, col] = find(mask>0);
        
        for m=1:length(row)
            factor = ceil(mask_H(row(m), col(m))/50)+3;
            if factor>8
                factor =8;
            end
            cx = floor(factor*sigma);
            sizex = 2*cx-1;
            
            mask(mask>0)=0;
            mask((row(m)-cx+1):(row(m)+cx-1),(col(m)-cx+1):(col(m)+cx-1)) = 1;
            
            crop_data = data((row(m)-cx+1):(row(m)+cx-1),(col(m)-cx+1):(col(m)+cx-1));
            H = mask_H(row(m), col(m));
            offsetm = bg(row(m), col(m));
            
            [x,y]=find(data.*mask>0);
            dots{1,end+1}.originalx = unique(x);
            dots{1,end}.originaly = unique(y);
            dots{1,end}.original = crop_data;
            dots{1,end}.offsetm = offsetm;
            dots{1,end}.H = H;
            dots{1,end}.cx = cx;
            dots{1,end}.cy = cx;
            dots{1,end}.sx = sigma;
            dots{1,end}.sy = sigma;
        end
    end

    function DisplayTrack(frame,selectedcell)
        
        %  Construct the main GUI figure
        scrsz=get(0,'ScreenSize'); %detect screen size
        guiW=scrsz(3)*0.9; %width of the GUI
        guiH=scrsz(4)*0.8; %height of the GUI
        MainPos=[guiW/10,guiH/10 ,guiW,guiH]; %position of the GUI
        
        fh=figure('Position',MainPos,...
            'MenuBar','none',...
            'Name','Tranalyze- Movie Analysis Tool',...
            'NumberTitle','off');
        set(fh,'KeyPressFcn',@KeyPressCB,...
            'ResizeFcn',@fhResizeFcn) %make the clicking above figure work
        KPF=uicontrol(fh,'KeyPressFcn',@KeyPressCB,'Position',[1,1,1,1]); %workaround to get the focus for KeyPressFcn
        
        % Construct buttons and menus
        %         fhctl=figure('MenuBar','None'); %deleteLB
        butSz=0.1; %size of buttons
        butLS=0.05+0.35-2.15*butSz; %distance between left of figure and menu buttons (as fraction of GUI fig)
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','Goto','Position',...
            [butLS-1.1*butSz,0.83,butSz,butSz],'Callback',{@iPadKeyPress,'g'})
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','<<','Position',...
            [butLS,0.83,butSz,butSz],'Callback',@runbackward)
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','<-','Position',...
            [butLS+1.1*butSz,0.83,butSz,butSz],'Callback',{@iPadKeyPress,'leftarrow'})
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','->','Position',...
            [butLS+2.2*butSz,0.83,butSz,butSz],'Callback',{@iPadKeyPress,'rightarrow'})
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','>>','Position',...
            [butLS+3.3*butSz,0.83,butSz,butSz],'Callback',@runforward)
        
        butSz=0.05;
        butLS=0.75; %redefine distance between left of figure and menu buttons (as fraction of GUI fig)
%         uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','Color','Position',...
%             [butLS, 0.85, butSz,butSz],'Callback',{@iPadKeyPress,'c'})
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','Boundary','Position',...
            [butLS+1.1*butSz,0.85,butSz,butSz],'Callback',{@iPadKeyPress,'b'})
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','add','Position',...
            [butLS+2.2*butSz,0.85,butSz,butSz],'Callback',{@iPadKeyPress,'a'})
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','delete','Position',...
            [butLS+3.3*butSz,0.85,butSz,butSz],'Callback',{@iPadKeyPress,'d'})
        
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','dBoundary','Position',...
            [butLS+1.1*butSz,0.48,butSz,butSz],'Callback',{@iPadKeyPress,'p'})
        
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','Pdots OF','Position',...
            [butLS+2.2*butSz,0.48,butSz,butSz],'Callback',{@iPadKeyPress,'u'})
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','Pdots NF','Position',...
            [butLS+3.3*butSz,0.48,butSz,butSz],'Callback',{@iPadKeyPress,'n'})
        
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','Unlink','Position',...
            [butLS+1.1*butSz,0.4,butSz,butSz],'Callback',{@iPadKeyPress,'z'})
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','Ldots OF','Position',...
            [butLS+2.2*butSz,0.4,butSz,butSz],'Callback',{@iPadKeyPress,'f'})
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','Ldots NF','Position',...
            [butLS+3.3*butSz,0.4,butSz,butSz],'Callback',{@iPadKeyPress,'k'})
        
%         uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','Fdots OF','Position',...
%             [butLS+2.2*butSz,0.32,butSz,butSz],'Callback',{@iPadKeyPress,'s'})
%         uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','Fdots NF','Position',...
%             [butLS+3.3*butSz,0.32,butSz,butSz],'Callback',{@iPadKeyPress,'t'})
        
        
        
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','zoom','Position',...
            [butLS+2.2*butSz,0.1,butSz,butSz],'Callback',@iPadZoom)
        uicontrol( 'Parent', fh, 'Units','normalized','Style','pushbutton','string','save','Position',...
            [butLS+3.3*butSz,0.1,butSz,butSz],'Callback',@CloseAll)
       
        % construct buttons for H_threshold and selectec channels
        ChannelGrp=uibuttongroup('Units','normalized','Position',[butLS+1.5*butSz,0.55,2.8*butSz,3.5*butSz]);
        checkbox{channel_num}=[];
        H_value{channel_num}=[];
        for n= 1:channel_num
            checkbox{n} = uicontrol(ChannelGrp,'Style','checkbox','Units','normalized',...
                'Position',[0.3,1-n/(channel_num+1),0.9,0.2],'String',FISH{n,1}.channel); %, 'FontSize', 13
            H_value{n} = uicontrol(ChannelGrp,'Style','edit','Units','normalized',...
                'Position',[0.05,1-n/(channel_num+1),0.2,0.2],'String', num2str(FISH{n,1}.H_thres_default,'%4.1f'));
        end
        
        
        % define the variables
        [imy,imx]=size(AllImg{1,1});
        AR=imx/imy; %movie aspect ratio (keep constant during figure resizing)
        %         set(fh,'MenuBar','None','KeyPressFcn',@KeyPressCB) %deleteLB
        %colormap(gray)
        iPad=0; %bydefault, the program runs on the main monitor, not on the iPad
        if ~exist('frame','var')
            frame=1;
        end
        State='view';%editing state: view, delete, add,
        StateText='';
        ColorCode=0;
        Boundary=1;
        dotBoundary = 1;
        if ~exist('selectedcell','var')
            selectedcell=[];
        end
        
        % plot the movie frames
        if channel_num ==1
            size_lim = 0.55;
        else
            size_lim = 1.1;
        end
        hPlotAxes{channel_num}=[];
        hLabelPlotAxes{channel_num} = [];
        HistAxes{channel_num}=[];
        for n = 1:channel_num
            hPlotAxes{n} = axes(...    % Axes for plotting the selected plot
                'Parent', fh, ...
                'Units', 'normalized', ...
                'Position',[0.05*n+(n-1)*size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]), 0.1,...
                size_lim/channel_num*[guiH/guiW*AR, 1]/max([guiH/guiW*AR, 1])]);
            axis([0,imx,0,imy])
            hLabelPlotAxes{n} = axes(...    % Axes for plotting all the labels
                'Parent', fh, ...
                'Units', 'normalized', ...
                'Position',[0.05*n+(n-1)*size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]), 0.1,...
                size_lim/channel_num*[guiH/guiW*AR, 1]/max([guiH/guiW*AR, 1])]);
            axis([0,imx,0,imy])
            HistAxes{n} = axes(...    % Axes for plotting the H_thres
                'Parent', fh, ...
                'Units', 'normalized', ...
                'Position',[0.05*n+(n-1)*size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]),...
                0.15+size_lim/channel_num/max([guiH/guiW*AR, 1]),...
                size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]), 0.1]);
            axis([0,size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]),0,0.1]);
        end
        
        % plot H_thres histogram
        for n = 1:channel_num
            set(fh,'CurrentAxes',HistAxes{n})
            hold off;
            if ~isempty(FISH{n,1}.X)
                x= FISH{n,1}.X; y = FISH{n,1}.f.a1*exp(-(x- FISH{n,1}.f.b1).^2/(FISH{n,1}.f.c1).^2);
                bar(FISH{n,1}.X, FISH{n,1}.Y, 'FaceColor', 'w', 'EdgeColor','b'); hold on;
                plot(x, y, 'k', 'LineWidth', 2);
                line([FISH{n,1}.H_thres_default, FISH{n,1}.H_thres_default],[1, max(y)], 'Color', 'red', 'LineWidth', 2);
                if FISH{n,1}.H_thres_default ~= FISH{n,1}.H_thres
                    line([FISH{n,1}.H_thres, FISH{n,1}.H_thres],[1, max(y)], 'Color', 'green', 'LineWidth', 2);
                end
                set(gca, 'YScale', 'log'); ylim([1,1.1*max(FISH{n,1}.Y)]);  xlim([0, max(4*FISH{n,1}.H_thres, 100)]); %xlim([0, max(prctile(x, 50), 100)]);
            end
        end
        
        % construct slider for image caxis
        caxis_low{channel_num} = [];
        caxis_high{channel_num} = [];
        for n= 1:channel_num
            caxis_low{n} = uicontrol( 'Parent', fh, 'Style','slider','Units','normalized',...
                'Position',[0.05*n+(n-1)*size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]),0.04,...
                size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]), 0.015], 'min', -0.1*FISH{1,1}.H_thres_default, 'max', 50,'Callback',@SetCaxis); %1.5*FISH{1,1}.H_thres_default
            caxis_high{n} = uicontrol( 'Parent', fh, 'Style','slider','Units','normalized',...
                'Position',[0.05*n+(n-1)*size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]),0.01,...
                size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]), 0.015], 'min', -0.1*FISH{1,1}.H_thres_default, 'max', 1000,'Callback',@SetCaxis); %1.5*FISH{1,1}.H_thres_default
            caxis_low{n}.Value = 0;
            caxis_high{n}.Value = 5*FISH{1,1}.H_thres_default;
        end
        
        plotframe;

        
        function plotframe(fastplotframe)
            if ~exist('fastplotframe','var')
                fastplotframe=0;
            end
            
            for num=1:channel_num
                im=AllImg{num,frame};   
                %im=log(double(im))*50/3-57*5/3;
                %im=(3+log10(max(0.001,double(im))));
                %{
            im(im<0)=0;
            im=im./max(im(:));
            im=log(im);
            %im=log(im+1);
            im=im-0.4*min(im(~isinf(im)));
            im=20*im./max(im(:));
                %}
                im = 100*(im-prctile(im(:),5))/prctile(im(:),95);
                
                Nborder=2; 
                Nprog=3.5;
                Ndesc=4;
                Napp=3;
                Ndisapp=5;
                Nsel=4.5;
                dNborder=9;
                d2Nborder = 6;
                
                IMborder=zeros(imy,imx);
                IMprog=zeros(imy,imx);
                IMdesc=zeros(imy,imx);
                IMapp=zeros(imy,imx);
                IMdisapp=zeros(imy,imx);
                IMselcell=zeros(imy,imx);
                IMborderSel=zeros(imy,imx);
                dIMborder=zeros(imy,imx);
                allIMborder= zeros(imy,imx);
                
                for cell=1:length(Tracked{frame}.cells)
                    curcell=Tracked{frame}.cells{cell};
                    cmask=zeros(double(curcell.size)+[2,2]);
                    curmask = get_cell_mask(curcell, num);
                    cmask(2:end-1,2:end-1)=curmask;
                    dpos=double(curcell.pos);
                    dsize=double(curcell.size);
                    border=cmask-imerode(cmask,strel('disk',2));
                    IMborder(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)=...
                        IMborder(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)+...
                        border(2:end-1,2:end-1);
                    if ~isfield(curcell,'progenitor')
                        curcell.progenitor=[];
                    end
                    if isempty(curcell.descendants)
                        IMdisapp(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)=...
                            IMdisapp(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)+curcell.mask;
                    elseif isempty(curcell.progenitor)
                        IMapp(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)=...
                            IMapp(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)+curcell.mask;
                    else
                        prevcell=Tracked{frame-1}.cells{curcell.progenitor};
                        if ~isscalar(curcell.descendants)
                            IMprog(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)=...
                                IMprog(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)+curcell.mask;
                        end
                        if ~isscalar(prevcell.descendants)
                            IMdesc(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)=...
                                IMdesc(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)+curcell.mask;
                        end
                    end
                    if any(selectedcell==cell)
                        IMselcell(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)=...
                            IMselcell(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)+curcell.mask;
                        IMborderSel(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)=...
                            IMborderSel(dpos(1):dpos(1)+dsize(1)-1,dpos(2):dpos(2)+dsize(2)-1)+...
                            border(2:end-1,2:end-1);
                    end
                    
                    if isfield(FISH{num, frame}.cells{cell}, 'dots')
                        dot = FISH{num, frame}.cells{cell}.dots;
                        dot_num = length(dot);
                        for i=1:dot_num
                            if ~isempty(dot{1,i})
                                dx = dot{1,i}.originalx + Tracked{frame}.cells{cell}.pos(1)-1;
                                dy = dot{1,i}.originaly + Tracked{frame}.cells{cell}.pos(2)-1;
                                if ~isfield(dot{1,i}, 'status')
                                    dIMborder(dx,min(dy)) = 1;
                                    dIMborder(dx,max(dy)) = 1;
                                    dIMborder(min(dx),dy) = 1;
                                    dIMborder(max(dx),dy) = 1;
                                elseif strcmp(dot{1,i}.status, type1)
                                    dIMborder(dx,min(dy)) = 2;
                                    dIMborder(dx,max(dy)) = 2;
                                    dIMborder(min(dx),dy) = 2;
                                    dIMborder(max(dx),dy) = 2;
                                elseif strcmp(dot{1,i}.status, type3) || strcmp(dot{1,i}.status, type6)
                                    dIMborder(dx,min(dy)) = 1;
                                    dIMborder(dx,max(dy)) = 1;
                                    dIMborder(min(dx),dy) = 1;
                                    dIMborder(max(dx),dy) = 1;
                                end
                            end
                        end
                    end
                end
                
                if ColorCode
                    %im(IMprog>0)=Nprog;
                    %im(IMdesc>0)=Ndesc;
                    %im(IMapp>0)=Napp;
                    %im(IMdisapp>0)=Ndisapp;
                    %%im(IMselcell>0)=Nsel; %this plots color filling selected cells
                    allIMborder(IMprog>0)=Nprog;
                    allIMborder(IMdesc>0)=Ndesc;
                    allIMborder(IMapp>0)=Napp;
                    allIMborder(IMdisapp>0)=Ndisapp;
                end
                if Boundary
                    %im(IMborder>0)=Nborder;
                    allIMborder(IMborder>0)=Nborder;
                end
                if dotBoundary
                    %im(dIMborder>0) = dNborder;
                    allIMborder(dIMborder==1) = dNborder;
                    allIMborder(dIMborder==2) = d2Nborder;
                end
                
                %im(IMborderSel>0)=Nsel; %this plots only color on the boundary of selected cell
                if fastplotframe
                    image(im(1:5:end,1:5:end))
                    axis(zoomax)
                else
                    set(fh,'CurrentAxes',hPlotAxes{num});
                    zoomax=axis;
                    
                    hold off;
                    imagesc(hPlotAxes{num}, im, 'CDataMapping', 'scaled'); 
                    colormap(hPlotAxes{num},'gray'); 
                    caxis(hPlotAxes{num}, [caxis_low{num}.Value caxis_high{num}.Value]);
                    hold on;
                    axis(hPlotAxes{num},zoomax); 
                    
                    set(fh,'CurrentAxes',hLabelPlotAxes{num});
                    h = imshow(allIMborder);
                    axis(hLabelPlotAxes{num},'off')
                    set(h, 'AlphaData', allIMborder>0); 
                    colormap(hLabelPlotAxes{num},'jet');
                    caxis(hLabelPlotAxes{num},[0 10]);
                    axis(hLabelPlotAxes{num},zoomax); 

                    linkaxes([hPlotAxes{:},hLabelPlotAxes{:}], 'xy');
                end
                
                selectedcellstr=num2str(selectedcell,'%d,');
                selectedcellstr=selectedcellstr(1:end-1);
                set(gcf,'name',['frame:',num2str(frame),' ', Tracked{frame}.filename{1},' #cell: (' ,selectedcellstr, ')/',num2str(length(Tracked{frame}.cells))])
                title(StateText)
                
                %give the focus to the keypressfcn uicontrol
                uicontrol(KPF)
            end
        end  
        
        function iPadKeyPress(src,evnt,key,mod) % button and shortcut
            evnt2.Key=key;
            evnt2.Modifier='';
            if exist('mod','var')
                evnt2.Modifier={mod};
            end
            figure(fh)
            zoom off
            KeyPressCB(src,evnt2);
        end
        function KeyPressCB(src,evnt)
            switch evnt.Key
                case 'leftarrow'
                    ccell=[Tracked{frame}.cells{selectedcell}];
                    firstframe=(frame==1);
                    frame=max(1,frame-1);
                    
                    if ~isempty(ccell)
                        if ~firstframe
                            selectedcell=[ccell.progenitor];
                            selectedcell=unique(selectedcell);
                        end
                    else
                        selectedcell=[];
                    end
                    plotframe
                case 'rightarrow'
                    ccell=[Tracked{frame}.cells{selectedcell}];
                    lastframe=(frame==length(Tracked));
                    frame=min(frame+1,length(Tracked));
                    
                    if ~isempty(ccell)
                        if ~lastframe
                            selectedcell=[ccell.descendants];
                            selectedcell=unique(selectedcell);
                        end
                    else
                        selectedcell=[];
                    end
                    plotframe
                case 'c' %show/hide cell colorcode
                    ColorCode = ~ColorCode;
                    plotframe
                case 'b' %show/hide dot boudary
                    Boundary=~Boundary;
                    plotframe
                case 'p' %show/hide dot boundary
                    dotBoundary = ~dotBoundary;
                    plotframe
                case 'd' %delete segment
                    DeleteSegment;
                    plotframe
                case 'a' %add segment, control=autoadd blob
                    AddSegment;
                    plotframe
                case 'g' %goto frame
                    fnum=inputdlg('Goto frame:','Goto frame:');
                    if ~isempty(fnum)
                        frame=str2num(char(fnum));
                    end
                    plotframe;
                case 'u' %find dots in this frame
                    find_dots_one_frame;
                    plotframe;
                case 'n' %find dots across all frames
                    find_dots_all_frames;
                    plotframe;
                case 'z' %unlink dots
                    unlink_dots;
                    plotframe;
                case 'f' %link dots in this frame
                    link_dots_one_frame;
                    plotframe;
                case 'k' %link dots across all frames
                    link_dots_all_frames;
                    plotframe;
                case 's' %fit dots in this frame
                    fit_dots_one_frame;
                    plotframe;
                case 't' %fit dots across all frames
                    fit_dots_all_frames;
                    plotframe;
            end
        end
        
        function fhResizeFcn(src,evnt)
            cPos=get(fh,'Position');
            guiW=cPos(3);
            guiH=cPos(4);
            %axes_size=0.7*[guiH/guiW*AR, 1]/max([guiH/guiW*AR, 1]);
            
            for k=1:channel_num
                set(hPlotAxes{k},...
                    'Position',[0.05*k+(k-1)*size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]), 0.1,...
                size_lim/channel_num*[guiH/guiW*AR, 1]/max([guiH/guiW*AR, 1])]);
                set(hLabelPlotAxes{k},...
                    'Position',[0.05*k+(k-1)*size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]), 0.1,...
                    size_lim/channel_num*[guiH/guiW*AR, 1]/max([guiH/guiW*AR, 1])]);
                set(HistAxes{k}, ...
                    'Position',[0.05*k+(k-1)*size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]),...
                0.15+size_lim/channel_num/max([guiH/guiW*AR, 1]),...
                size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]), 0.1]);
                set(caxis_low{k},...
                    'Position',[0.05*k+(k-1)*size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]),0.04,...
                    size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]), 0.015], 'min', -0.1*FISH{1,1}.H_thres_default, 'max', 1.5*FISH{1,1}.H_thres_default,'Callback',@SetCaxis);
                set(caxis_high{k},...
                    'Position',[0.05*k+(k-1)*size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]),0.01,...
                    size_lim/channel_num*guiH/guiW*AR/max([guiH/guiW*AR, 1]), 0.015], 'min', -0.1*FISH{1,1}.H_thres_default, 'max', 1.5*FISH{1,1}.H_thres_default,'Callback',@SetCaxis);
            end
        end
        
        function runforward(src,evnt) % button ">>"
            if get(src,'UserData')
                %stop running
                %curzoom=axis(get(fh,'CurrentAxes'));
                %figure(fh)
                %axis(curzoom*5);
                set(src,'UserData',0)
                set(src,'BackgroundColor',[0.7,0.7,0.7])
                %plotframe
            else
                %start running
                %curzoom=axis(get(fh,'CurrentAxes'));
                %figure(fh)
                %axis(curzoom/5);
                set(src,'UserData',1)
                set(src,'BackgroundColor',[1,0,0])
            end
            while get(src,'UserData')
                ccell=[Tracked{frame}.cells{selectedcell}];
                lastframe=(frame==length(Tracked));
                frame=min(frame+1,length(Tracked));
                
                if ~isempty(ccell)
                    if ~lastframe
                        selectedcell=[ccell.descendants];
                        selectedcell=unique(selectedcell);
                    end
                else
                    selectedcell=[];
                end
                plotframe
                drawnow
            end
        end
        function runbackward(src,evnt) % button "<<"
            if get(src,'UserData')
                set(src,'UserData',0)
                set(src,'BackgroundColor',[0.7,0.7,0.7])
            else
                set(src,'UserData',1)
                set(src,'BackgroundColor',[1,0,0])
            end
            while get(src,'UserData')
                ccell=[Tracked{frame}.cells{selectedcell}];
                firstframe=(frame==1);
                frame=max(1,frame-1);
                
                if ~isempty(ccell)
                    if ~firstframe
                        selectedcell=[ccell.progenitor];
                        selectedcell=unique(selectedcell);
                    end
                else
                    selectedcell=[];
                end
                plotframe
                drawnow
            end
        end
        
        function iPadZoom(src,evnt) % button "Zoom"
            if strcmp(get(zoom(gcf),'Enable'),'off')
                set(gcf,'WindowButtonDownFcn',[])
                set(gcf,'WindowButtonUpFcn',[])
            end
            State='view';
            StateText='';
            zoom
            linkaxes([hPlotAxes{:},hLabelPlotAxes{:}],'xy')
        end
        function CloseAll(src,evnt) % button 'save'
            export2wsdlg({'Tracked Data','Dot Data'},{'Tracked','FISH'},{Tracked,FISH});
            %            close(fhctl);
            %            close(fh);
        end 
        
        function SetCaxis(src,evnt)
            for num = 1:channel_num
                caxis(hPlotAxes{num}, [caxis_low{num}.Value caxis_high{num}.Value]);
            end
        end
        
        function AddSegment % button "add"
            if strcmp(State,'add')
                set(gcf,'WindowButtonDownFcn',[])
                set(gcf,'WindowButtonUpFcn',[])
                State='view';
                StateText='';
            else
                set(gcf,'WindowButtonDownFcn',@btndown)
                set(gcf,'WindowButtonUpFcn',@btnup)
                State='add';
                StateText='Mark Region To Add';
                lh=[];
                newseg=[];
                
            end
            
            function btndown(src,evnt)
                lh=line('Visible','off');
                newseg=[];
                p=get(gca,'CurrentPoint');
                coord=p(1,[2,1]);
                newseg(end+1,:)=coord;
                set(lh,'XData',newseg(:,2),'YData',newseg(:,1),'Marker','none','Color','r','Visible','on');
                set(src,'WindowButtonMotionFcn',@move)
            end
            function move(src,evnt)
                p=get(gca,'CurrentPoint');
                coord=p(1,[2,1]);
                steps=1+ceil(max(abs(newseg(end,:)-coord)));
                newseg=[newseg;[linspace(newseg(end,1),coord(1),steps); linspace(newseg(end,2),coord(2),steps)]'];
                %newseg(end+1,:)=coord;
                set(lh,'XData',newseg(:,2),'YData',newseg(:,1),'Marker','none','Color','r','Visible','on');
            end
            function btnup(src,evnt)
                coord=newseg(1,:);
                steps=1+ceil(max(abs(newseg(end,:)-coord)));
                newseg=[newseg;[linspace(newseg(end,1),coord(1),steps); linspace(newseg(end,2),coord(2),steps)]'];
                set(src,'WindowButtonMotionFcn',[])
                newsegmask=zeros(imy,imx);
                newsegind=sub2ind(size(newsegmask),round(newseg(:,1)),round(newseg(:,2)));
                newsegmask(newsegind)=1;
                newsegmask=imerode(imfill(imdilate(newsegmask,strel('diamond',1))),strel('diamond',1));
                bbox=regionprops(newsegmask,'BoundingBox');
                cellslice={floor(bbox.BoundingBox(2))+1:floor(bbox.BoundingBox(2)+bbox.BoundingBox(4)),...
                    floor(bbox.BoundingBox(1))+1:floor(bbox.BoundingBox(1)+bbox.BoundingBox(3))};
                if ~isempty(Tracked{frame}.cells)
                    Tracked{frame}.cells{end+1}=struct(Tracked{frame}.cells{end});
                    for cfield=fieldnames(Tracked{frame}.cells{end})'
                        Tracked{frame}.cells{end}.(cfield{1})=[];
                    end
                else
                    Tracked{frame}.cells{1}=struct('mask',[],'pos',[],'size',[],'progenitor',[],'descendants',[]);
                end
                Tracked{frame}.cells{end}.mask=newsegmask(cellslice{1},cellslice{2});
                Tracked{frame}.cells{end}.pos=floor(bbox.BoundingBox(2:-1:1))+1;
                Tracked{frame}.cells{end}.size=size(Tracked{frame}.cells{end}.mask);
                Tracked{frame}.cells{end}=CalcCellProperties(Tracked{frame}.cells{end},AllImg{frame});
                
                for m = 1:channel_num
                    num_cell = length(Tracked{frame}.cells);
                    FISH{m, frame}.cells{num_cell}=[];
                    if checkbox{m}.Value~=0
                        im_bs = AllImg{m,frame};
                        pos_x = Tracked{frame}.cells{end}.pos(1);
                        pos_y = Tracked{frame}.cells{end}.pos(2);
                        size_x = Tracked{frame}.cells{end}.size(1);
                        size_y = Tracked{frame}.cells{end}.size(2);
                        cell_image = Tracked{frame}.cells{end}.mask.*im_bs(pos_x:pos_x+size_x-1, pos_y:pos_y+size_y-1);
                        [FISH{m, frame}.cells{num_cell}.mask_H, FISH{m, frame}.cells{num_cell}.bg] = dot_mask(cell_image);
                        pickdots(frame, m, num_cell);
                    end
                end
                plotframe;
            end
        end
        function DeleteSegment % button "delete"
            if strcmp(State,'delete')
                set(gcf,'WindowButtonDownFcn',[])
                set(gcf,'WindowButtonUpFcn',[])
                State='view';
                StateText='';
            else
                set(gcf,'WindowButtonDownFcn',@btndown)
                set(gcf,'WindowButtonUpFcn',[])
                State='delete';
                StateText='Select Cell To Delete';
            end
            
            function btndown(src,evnt)
                p=get(gca,'CurrentPoint');
                coord=p(1,[2,1]);
                allpos=cell2mat(cellfun(@(x) double(x.pos),Tracked{frame}.cells,'Uniform',0)');
                allsize=cell2mat(cellfun(@(x) double(x.size),Tracked{frame}.cells,'Uniform',0)');
                isincell=all(bsxfun(@minus,allsize+allpos,coord)>0 & bsxfun(@minus,allpos,coord)<0,2);
                clicked=find(isincell,1);
                if isempty(clicked)
                    return
                end
                pro=Tracked{frame}.cells{clicked}.progenitor;
                if ~isempty(pro)
                    prodes=Tracked{frame-1}.cells{pro}.descendants;
                    %delete this cell from its progenitor
                    if isscalar(prodes)
                        Tracked{frame-1}.cells{pro}.descendants=[];
                    else
                        Tracked{frame-1}.cells{pro}.descendants(prodes==clicked)=[];
                    end
                end
                if frame>1
                    %renumber the other 'cousins' in their parents
                    for ccell=1:length(Tracked{frame-1}.cells)
                        cousins=Tracked{frame-1}.cells{ccell}.descendants;
                        Tracked{frame-1}.cells{ccell}.descendants=cousins-(cousins>clicked);
                    end
                end
                for des=Tracked{frame}.cells{clicked}.descendants
                    Tracked{frame+1}.cells{des}.progenitor=[];
                end
                if frame<length(Tracked)
                    %renumber the other 'cousins' in their children
                    for ccell=1:length(Tracked{frame+1}.cells)
                        cousins=Tracked{frame+1}.cells{ccell}.progenitor;
                        Tracked{frame+1}.cells{ccell}.progenitor=cousins-(cousins>clicked);
                    end
                end
                Tracked{frame}.cells(clicked)=[];
                Tracked{frame}.Locked=0;
                for num = 1:channel_num
                    FISH{num, frame}.cells(clicked)=[];
                end
                plotframe;
            end
        end
        
        function find_dots_one_frame % button "Pdot OF"
            hh = waitbar(0,'Identify dots in selected Channels');
            for m = 1:channel_num
                waitbar(m/channel_num,hh)
                if checkbox{m}.Value ~= 0
                    FISH{m,1}.H_thres = str2num(H_value{m}.String);
                    pickdots(frame, m);
                    
                    if ~isempty(FISH{m,1}.X)
                        x= FISH{m,1}.X; y = FISH{m,1}.f.a1*exp(-(x- FISH{m,1}.f.b1).^2/(FISH{m,1}.f.c1).^2);
                        cla(HistAxes{m}); hold on;
                        bar(HistAxes{m}, FISH{m,1}.X, FISH{m,1}.Y, 'FaceColor', 'w', 'EdgeColor','b'); hold on;
                        plot(HistAxes{m},x, y, 'k', 'LineWidth', 2);
                        line(HistAxes{m}, [FISH{m,1}.H_thres_default, FISH{m,1}.H_thres_default],[1, max(y)], 'Color', 'red', 'LineWidth', 2);
                        if FISH{m,1}.H_thres_default ~= FISH{m,1}.H_thres
                            line(HistAxes{m}, [FISH{m,1}.H_thres, FISH{m,1}.H_thres],[1, max(y)], 'Color', 'green', 'LineWidth', 2);
                        end
                        set(gca, 'YScale', 'log'); ylim([1,1.1*max(FISH{n,1}.Y)]); xlim([0, max(prctile(x, 50), 100)]);
                    end
                end
            end
            delete(hh)
        end
        function find_dots_all_frames % button "Pdot NF"
            for m = 1:channel_num
                hh = waitbar(0,strcat('Identify dots in Channel', checkbox{m}.String));
                if checkbox{m}.Value ~= 0
                    FISH{m,1}.H_thres = str2num(H_value{m}.String);
                    for cframe = 1:length(Tracked)
                        waitbar(cframe/length(Tracked),hh)
                        pickdots(cframe, m);
                    end
                    
                    x= FISH{m,1}.X; y = FISH{m,1}.f.a1*exp(-(x- FISH{m,1}.f.b1).^2/(FISH{m,1}.f.c1).^2);
                    cla(HistAxes{m}); hold on;
                    bar(HistAxes{m}, FISH{m,1}.X, FISH{m,1}.Y, 'FaceColor', 'w', 'EdgeColor','b'); hold on;
                    plot(HistAxes{m},x, y, 'k', 'LineWidth', 2);
                    line(HistAxes{m}, [FISH{m,1}.H_thres_default, FISH{m,1}.H_thres_default],[1, max(y)], 'Color', 'red', 'LineWidth', 2);
                    if FISH{m,1}.H_thres_default ~= FISH{m,1}.H_thres
                        line(HistAxes{m}, [FISH{m,1}.H_thres, FISH{m,1}.H_thres],[1, max(y)], 'Color', 'green', 'LineWidth', 2);
                    end
                    set(gca, 'YScale', 'log'); ylim([1,1.1*max(FISH{n,1}.Y)]); xlim([0, max(prctile(x, 50), 100)]);
                end
                delete(hh)
            end
        end
        
        function unlink_dots % button "Unlink"
            for cframe = 1:length(FISH)
                if isfield(FISH{1,cframe}, 'cells')
                    for num=1:length(FISH{1,cframe}.cells)
                        if isfield(FISH{1,cframe}.cells{1,num}, 'dots')
                            for n_dots = 1:length(FISH{1,cframe}.cells{1,num}.dots)
                                if isfield(FISH{1,cframe}.cells{1,num}.dots{n_dots},'status')
                                    FISH{1,cframe}.cells{1,num}.dots{n_dots} = rmfield(FISH{1,cframe}.cells{1,num}.dots{n_dots},'status');
                                end
                            end
                        end
                        if isfield(FISH{2,cframe}.cells{1,num}, 'dots')
                            for n_dots = 1:length(FISH{2,cframe}.cells{1,num}.dots)
                                if isfield(FISH{2,cframe}.cells{1,num}.dots{n_dots},'status')
                                    FISH{2,cframe}.cells{1,num}.dots{n_dots} = rmfield(FISH{2,cframe}.cells{1,num}.dots{n_dots},'status');
                                end
                            end
                        end
                    end
                end
            end
        end
        
        function link_dots_one_frame % button "Ldot OF"
            FISHintron = FISH(1,frame);
            FISHexon1 = FISH(2,frame);
            channel_intron = FISH{1,1}.channel;
            channel_exon1 = FISH{2,1}.channel;
            
            % displacement the dots (due to dichoric channels
            % 405/488/561/640 Quad
            % 445/515/594 Triple  (0, 5)
            disp_x = 0;
            disp_y = 0;
            if  cellfun(@(x) ~isempty(x),strfind(channel_intron,'445'))...
                    ||  cellfun(@(x) ~isempty(x),strfind(channel_intron,'514'))...
                    ||  cellfun(@(x) ~isempty(x),strfind(channel_intron,'594'))
                FISHintron = displace_channel(FISHintron, disp_x, disp_y);
            end
            if  cellfun(@(x) ~isempty(x),strfind(channel_exon1,'445'))...
                    ||  cellfun(@(x) ~isempty(x),strfind(channel_exon1,'514'))...
                    ||  cellfun(@(x) ~isempty(x),strfind(channel_exon1,'594'))
                FISHexon1 = displace_channel(FISHexon1, disp_x, disp_y);
            end
            
            % co-localize dots and label them
            dot_dist_limit = 2.5;
            [FISHintron, FISHexon1] = label_dots_2color(FISHintron, FISHexon1, dot_dist_limit, type1, type3, type6);
            
            % label the original documents
            hh = waitbar(0,'link dots across Channels');
            waitbar(0.5,hh)
            for num=1:length(FISH{1,frame}.cells)
                if isfield(FISH{1,frame}.cells{1,num}, 'dots')
                    for n_dots = 1:length(FISH{1,frame}.cells{1,num}.dots)
                        FISH{1,frame}.cells{1,num}.dots{n_dots}.status = FISHintron{1,1}.cells{1,num}.dots{n_dots}.status;
                    end
                    for n_dots = 1:length(FISH{2,frame}.cells{1,num}.dots)
                        FISH{2,frame}.cells{1,num}.dots{n_dots}.status = FISHexon1{1,1}.cells{1,num}.dots{n_dots}.status;
                    end
                end
            end
            delete(hh);
        end
        function link_dots_all_frames % button "Ldot NF"
            FISHintron = FISH(1,:);
            FISHexon1 = FISH(2,:);
            channel_intron = FISH{1,1}.channel;
            channel_exon1 = FISH{2,1}.channel;
            
            % displacement the dots (due to dichoric channels
            % 405/488/561/640 Quad
            % 445/515/594 Triple  (0, 5)
            disp_x = 0;
            disp_y = 0;
            if  cellfun(@(x) ~isempty(x),strfind(channel_intron,'445'))...
                    ||  cellfun(@(x) ~isempty(x),strfind(channel_intron,'514'))...
                    ||  cellfun(@(x) ~isempty(x),strfind(channel_intron,'594'))
                FISHintron = displace_channel(FISHintron, disp_x, disp_y);
            end
            if  cellfun(@(x) ~isempty(x),strfind(channel_exon1,'445'))...
                    ||  cellfun(@(x) ~isempty(x),strfind(channel_exon1,'514'))...
                    ||  cellfun(@(x) ~isempty(x),strfind(channel_exon1,'594'))
                FISHexon1 = displace_channel(FISHexon1, disp_x, disp_y);
            end
            
            % co-localize dots and label them
            dot_dist_limit = 2.5;
            [FISHintron, FISHexon1] = label_dots_2color(FISHintron, FISHexon1, dot_dist_limit, type1, type3, type6);
            
            % label the original documents
            hh = waitbar(0,'link dots across Channels');
            for cframe = 1:length(Tracked)
                waitbar(cframe/length(Tracked),hh)
                if isfield(FISH{1,cframe}, 'cells')
                    for num=1:length(FISH{1,cframe}.cells)
                        if isfield(FISH{1,cframe}.cells{1,num}, 'dots')
                            for n_dots = 1:length(FISH{1,cframe}.cells{1,num}.dots)
                                FISH{1,cframe}.cells{1,num}.dots{n_dots}.status = FISHintron{1,cframe}.cells{1,num}.dots{n_dots}.status;
                            end
                            for n_dots = 1:length(FISH{2,cframe}.cells{1,num}.dots)
                                FISH{2,cframe}.cells{1,num}.dots{n_dots}.status = FISHexon1{1,cframe}.cells{1,num}.dots{n_dots}.status;
                            end
                        end
                    end
                end
            end
            delete(hh);
        end

    end

end

function im =loadImage(filename)

im={};
for cfilename=filename'
    disp(char(cfilename))
    im{end+1}=imread(char(cfilename));
end
im=sum(cat(3, im{:}),3);

end
function cellsDictNew=CalcCellProperties(cellsDict,imn)
% Calculate properties of cells
% assume existing: pos, size, mask
% area, Acom (area-center-of-mass), Ftotal, Fmean, Fmax, Fpixels
cellsDictNew=cellsDict;
nbcell=length(cellsDict);
for cell=1:nbcell
    %if there is an 'Fmask' then it is the percent of F in every pixel that belongs to that cell. if not it is ones.
    if ~isfield(cellsDictNew(cell),'Fmask') || isempty(cellsDictNew(cell).Fmask)
        cellsDictNew(cell).Fmask=double(cellsDictNew(cell).mask);
    end
    cellsDictNew(cell).area=sum(cellsDictNew(cell).mask(:));
    cellsDictNew(cell).Acom=...
        floor([sum(sum(cellsDictNew(cell).mask,2).*(1:cellsDictNew(cell).size(1))')/cellsDictNew(cell).area,...
        sum(sum(cellsDictNew(cell).mask,1).*(1:cellsDictNew(cell).size(2)))/cellsDictNew(cell).area]);
    cellsDictNew(cell).Fpixels=double(imn(cellsDictNew(cell).pos(1):cellsDictNew(cell).pos(1)+cellsDictNew(cell).size(1)-1,...
        cellsDictNew(cell).pos(2):cellsDictNew(cell).pos(2)+cellsDictNew(cell).size(2)-1)).*cellsDictNew(cell).Fmask;
    cellsDictNew(cell).Ftotal=sum(cellsDictNew(cell).Fpixels(:));
    cellsDictNew(cell).Fmax=max(cellsDictNew(cell).Fpixels(:));
    cellsDictNew(cell).Fmean=cellsDictNew(cell).Ftotal/cellsDictNew(cell).area;
end
end


%% due to 2 separate dichroics in the confocal, channel displaces from
% each other
% 405/488/561/640 Quad
% 445/515/594 Triple  (1, 5)
function FISHselected = displace_channel(FISHselected, distx, disty)

%need displacement
% FISH{1,n}.cells{1,i}.dots.originalx -> original region
% FISH{1,n}.cells{1,i}.dots.originaly -> original region


%keep as it is
% FISH{1,n}.cells{1,i}.dots.integral
% FISH{1,n}.cells{1,i}.dots.sx
% FISH{1,n}.cells{1,i}.dots.PeakOD
% FISH{1,n}.cells{1,i}.dots.offset
% FISH{1,n}.cells{1,i}.dots.thres
% FISH{1,n}.cells{1,i}.dots.offsetm
% FISH{1,n}.cells{1,i}.dots.fit
% FISH{1,n}.cells{1,i}.dots.cx
% FISH{1,n}.cells{1,i}.dots.cy

Frame = length(FISHselected);

for n=1:1:Frame
    if isfield(FISHselected{1,n},'cells')==0 % this frame does not have cells
        continue;
    end
    N = length(FISHselected{1,n}.cells);
    for i=1:1:N
        num = length(FISHselected{1,n}.cells{1,i}.dots);
        for m=1:num
            FISHselected{1,n}.cells{1,i}.dots{1,m}.originalx = FISHselected{1,n}.cells{1,i}.dots{1,m}.originalx + distx;
            FISHselected{1,n}.cells{1,i}.dots{1,m}.originaly = FISHselected{1,n}.cells{1,i}.dots{1,m}.originaly + disty;
        end
    end
end

end


%% label status of all dots: whole transcripts, only intron, only exon
function [FISHintron, FISHexon1] = label_dots_2color(FISHintron, FISHexon1,dot_dist_limit, type1, type3, type6)

% FISH{1,n}.cells{1,i}.dots.maskcx -> original dot position
% FISH{1,n}.cells{1,i}.dots.maskcy -> original dot position
% FISH{1,n}.cells{1,i}.dots.originalx -> original region
% FISH{1,n}.cells{1,i}.dots.originaly -> original region
% FISH{1,n}.cells{1,i}.dots.integral
% FISH{1,n}.cells{1,i}.dots.cx
% FISH{1,n}.cells{1,i}.dots.cy
% FISH{1,n}.cells{1,i}.dots.sx
% FISH{1,n}.cells{1,i}.dots.PeakOD
% FISH{1,n}.cells{1,i}.dots.offset
% FISH{1,n}.cells{1,i}.dots.thres
% FISH{1,n}.cells{1,i}.dots.offsetm

Frame = length(FISHexon1);
for n=1:1:Frame        
    if isfield(FISHexon1{1,n},'cells')==0 % this frame does not have cells
        continue;
    end
    N = length(FISHexon1{1,n}.cells); % Number of cells in this Frame
    for i=1:1:N
        if isfield(FISHexon1{1,n}.cells{1,i}, 'dots')
            [FISHintron{1,n}.cells{1,i}.dots, FISHexon1{1,n}.cells{1,i}.dots]...
                = common_dots(FISHintron{1,n}.cells{1,i}.dots, FISHexon1{1,n}.cells{1,i}.dots, dot_dist_limit, type1, type3, type6);
        end
    end
end

end
function [dotIntron, dotExon1] = common_dots(dotIntron, dotExon1, dot_dist_limit, type1, type3, type6)

% re-organize the dots, as 'cell' is very hard to work with...
Exon1 = reorg(dotExon1);
Intron = reorg(dotIntron);

% search along Exon1
num = size(Exon1,1);
for m=1:num
    if isfield(dotExon1{1,m},'status') == 1 || isempty(Exon1)==1
        continue;
    else
        if isempty(Intron) == 0 % there are dots in Intron channel
            index01 = (abs(Intron(:,1)- Exon1(m,1))<dot_dist_limit).*(abs(Intron(:,2) - Exon1(m,2))<dot_dist_limit);
            if sum(index01) == 1 %find the dot in Intron and Exon1 channel
                if isfield(dotIntron{1,find(index01>0,1)},'status') %this dot already co-localize with another dots
                    dotExon1{1,m}.status = type6;
                else
                    dotExon1{1,m}.status = type1;
                    dotIntron{1,find(index01>0,1)}.status = type1;
                end
            elseif sum(index01) == 0 %find no dot in Intron channel neither
                dotExon1{1,m}.status = type6;
            else %find more than one overlapped dots 
                %sum(index01)
                %disp('Exon1 find more than one overlapped dots in the Intron channel -2')
                
                distD = zeros(1:sum(index01));
                for n_dots = 1:sum(index01)
                    if isfield(dotIntron{1,find(index01>0,1)},'status') %this dot already co-localize with another dots
                        distD(n_dots) = 100;
                    else
                        distD(n_dots) = sqrt((abs(Intron(n_dots,1)- Exon1(m,1))^2 + (abs(Intron(n_dots,2) - Exon1(m,2))^2)));
                    end
                end
                if min(distD) == 100 % all found dots already co-localize with other dots
                    dotExon1{1,m}.status = type6;
                else
                    dotExon1{1,m}.status = type1;
                    dotIntron{1,find(distD == min(distD),1)}.status = type1;
                end
            end
        else  % there is no dot in Intron channel
            dotExon1{1,m}.status = type6;
        end
    end
end


% search along Intron (ignore Exon1, where both of them all labeled)

num = size(Intron,1);
for m=1:num
    if isfield(dotIntron{1,m},'status') == 1 || isempty(Intron)==1
        continue;
    else
        dotIntron{1,m}.status = type3;
    end
end


end
function matrix = reorg(dots)

num = length(dots);
matrix = [];
for m=1:num
    matrix(m,1) = dots{1,m}.cx + min(dots{1,m}.originalx);
    matrix(m,2) = dots{1,m}.cy + min(dots{1,m}.originaly);
end

end

